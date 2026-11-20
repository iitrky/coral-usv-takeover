"""
Full experimental pipeline for CORAL (one seed per call).
usage: python run_experiments.py --seed 0 --out results/
"""
import argparse, json, os, time
import numpy as np
from sklearn.metrics import roc_auc_score, average_precision_score

from coral.sim import generate as _gen_sim, D_SAFE as _DS_SIM, HORIZON
from coral.ais_replay import load_tracks, generate_ais

SOURCE = "sim"
AIS_DIR = os.environ.get("CORAL_AIS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ct_dma"))
_POOLS = {}
D_SAFE = _DS_SIM


def generate(n, rng, split="train", **kw):
    if SOURCE == "sim":
        return _gen_sim(n, rng, **kw)
    f = {"train": "train", "cal": "valid", "test": "test"}[split]
    if f not in _POOLS:
        _POOLS[f] = load_tracks(f"{AIS_DIR}/ct_dma_{f}.pkl")
    kw = {k: v for k, v in kw.items() if k in ("sea", "ais_drop", "ais_age", "link_probs")}
    return generate_ais(_POOLS[f], n, rng, **kw)
from coral.model import Ensemble
from coral import conformal as cf
from coral.fleet import simulate

GRID = np.linspace(0.0, 1.0, 2001)
ALPHA = 0.02
FLEET = dict(K=24, M_ops=2, r_e=1 / 60.0)
KAPPA = 1.0
GAMMA = 0.005           # bound on late takeovers among hazards (CORAL-L)
TAU_H_Q = 20.0 * np.exp(0.4 * 1.2816)  # 90th percentile human time

OOD_SPECS = {
    "rough_sea": dict(sea=(0.7, 1.0)),
    "ais_dropout": dict(ais_drop=0.6),
    "dense_traffic": dict(n_targets=(5, 8)),
    "high_speed_craft": dict(tgt_speed=(12.0, 22.0)),
    "link_degradation": dict(link_probs=(0.3, 0.3, 0.4)),
}


def ece(y, p, bins=15):
    e = 0.0
    edges = np.linspace(0, 1, bins + 1)
    for a, b in zip(edges[:-1], edges[1:]):
        s = (p >= a) & (p < b) if b < 1 else (p >= a) & (p <= b)
        if s.any():
            e += s.mean() * abs(p[s].mean() - y[s].mean())
    return float(e)


def pred_metrics(y, p):
    pc = np.clip(p, 1e-7, 1 - 1e-7)
    return dict(auroc=float(roc_auc_score(y, p)), auprc=float(average_precision_score(y, p)),
                brier=float(np.mean((p - y) ** 2)), ece=ece(y, p),
                nll=float(-np.mean(y * np.log(pc) + (1 - y) * np.log(1 - pc))))


def rule_scores(d):
    """Classical CPA/TCPA alert logic from fused sensor estimates."""
    dcpa = d["X"][:, :, 7] * 1000.0
    tcpa = d["X"][:, :, 8]
    ahead = d["X"][:, :, 9] > 0
    valid = (d["M"] > 0) & ahead & (tcpa < 0.999)
    dc = np.where(valid, dcpa, np.inf).min(1)
    dec = np.full(len(dc), cf.PROCEED, np.int8)
    dec[dc < 2.5 * D_SAFE] = cf.TAKEOVER
    dec[dc < 1.5 * D_SAFE] = cf.AVOID
    return dec


def two_threshold_from_rates(r, y, groups, alpha, beta_global, r2):
    """global (non-stratified) CRC thresholds, SCRC-style two-stage."""
    lo = cf.calibrate_lo(r, y, groups, alpha, GRID, stratified=False)
    beta = cf.uniform_budgets(groups, beta_global)
    return lo, beta


def run(seed, out):
    t0 = time.time()
    rng = np.random.default_rng(seed)
    big = SOURCE == "sim"
    tr = generate(40000 if big else 30000, rng, "train"); va = generate(5000 if big else 4000, rng, "cal")
    c1 = generate(6000, rng, "cal"); c2 = generate(6000, rng, "cal"); te = generate(20000 if big else 15000, rng, "test")
    specs = OOD_SPECS if big else {k: v for k, v in OOD_SPECS.items() if k in ("rough_sea", "ais_dropout", "link_degradation")}
    ood = {k: generate(8000 if big else 6000, rng, "test", **v) for k, v in specs.items()}
    for d in [tr, va, c1, c2, te] + list(ood.values()):
        d.pop("natural_hazard_rate", None)
    print(f"[seed {seed}] data {time.time()-t0:.0f}s", flush=True)

    F, Cd = tr["X"].shape[2], tr["C"].shape[1]
    nets = {
        "LCSA": Ensemble(F, Cd, m=5),
        "MLP-set": Ensemble(F, Cd, m=5, attention=False),
        "LCSA-noctx": Ensemble(F, Cd, m=5, use_context=False),
    }
    for k, e in nets.items():
        e.fit(tr["X"], tr["M"], tr["C"], tr["y"], epochs=15)
        e.calibrate(va["X"], va["M"], va["C"], va["y"])
        print(f"[seed {seed}] trained {k} {time.time()-t0:.0f}s", flush=True)

    def P(net, d):
        return nets[net].predict(d["X"], d["M"], d["C"])

    def P_single(d):
        p, _ = nets["LCSA"].members[0].predict_proba(d["X"], d["M"], d["C"])
        return p, np.zeros_like(p)

    preds = {}
    for name in nets:
        preds[name] = {s: P(name, d) for s, d in [("c1", c1), ("c2", c2), ("te", te)] + list(ood.items())}
    preds["LCSA-single"] = {s: P_single(d) for s, d in [("c1", c1), ("c2", c2), ("te", te)] + list(ood.items())}

    # save predictions and decision-relevant fields for post-hoc analyses (frontiers, re-calibration)
    keep = ("y", "link", "tcpa_true", "est_tcpa", "bw", "rtt")
    save = {}
    for split, d in [("c1", c1), ("c2", c2), ("te", te)] + list(ood.items()):
        save[f"{split}__pm"], save[f"{split}__ps"] = preds["LCSA"][split]
        for k in keep:
            save[f"{split}__{k}"] = d[k]
    np.savez_compressed(os.path.join(out, f"seed{seed}_preds.npz"), **save)
    R = dict(seed=seed, predictor={}, methods={}, ood={}, sweeps={}, group_validity={})
    # ---------------- predictor quality ----------------
    for name in preds:
        R["predictor"][name] = {"test": pred_metrics(te["y"], preds[name]["te"][0])}
        for s in ood:
            R["predictor"][name][s] = pred_metrics(ood[s]["y"], preds[name][s][0])
    # epistemic OOD detection (sigma): ID test vs each OOD set
    R["ood_detect"] = {}
    for s in ood:
        sid = preds["LCSA"]["te"][1]; sod = preds["LCSA"][s][1]
        lab = np.r_[np.zeros(len(sid)), np.ones(len(sod))]
        R["ood_detect"][s] = float(roc_auc_score(lab, np.r_[sid, sod]))

    budgets = cf.workload_budgets(c2["link"], c2["bw"], c2["rtt"], **FLEET)
    R["budgets"] = {int(k): v for k, v in budgets.items()}

    # ---------------- method factory ----------------
    def coral(net="LCSA", kappa=KAPPA, stratified=True, workload=True, alpha=ALPHA, budget_override=None):
        pm1, ps1 = preds[net]["c1"]; pm2, ps2 = preds[net]["c2"]
        r1 = cf.score(pm1, ps1, kappa); r2 = cf.score(pm2, ps2, kappa)
        lo = cf.calibrate_lo(r1, c1["y"], c1["link"], alpha, GRID, stratified=stratified)
        if budget_override is not None:
            bud = budget_override
        elif workload:
            bud = budgets
        else:
            # same mean budget, uniform across regimes
            w = np.array([np.mean(c2["link"] == g) for g in sorted(budgets)])
            bud = cf.uniform_budgets(c2["link"], float(np.dot(w, [budgets[g] for g in sorted(budgets)])))
        hi = cf.calibrate_hi(r2, c2["link"], lo, bud, GRID)

        def apply(split, d):
            pm, ps = preds[net][split]
            return cf.decide(cf.score(pm, ps, kappa), d["link"], lo, hi)
        return apply, lo, hi

    def threshold_only(split, d):
        pm, _ = preds["LCSA"][split]
        return np.where(pm >= 0.5, cf.AVOID, cf.PROCEED).astype(np.int8)

    # matched budget for selective baselines: realised takeover rate of CORAL on cal2
    ours_apply, ours_lo, ours_hi = coral()
    tk_rate_cal = float(np.mean(ours_apply("c2", c2) == cf.TAKEOVER))
    R["matched_takeover_rate"] = tk_rate_cal

    def selective_conf(split, d):
        pm, _ = preds["LCSA"][split]
        pmc, _ = preds["LCSA"]["c2"]
        conf_c = np.abs(pmc - 0.5)
        thr = np.quantile(conf_c, tk_rate_cal)
        dec = np.where(pm >= 0.5, cf.AVOID, cf.PROCEED).astype(np.int8)
        dec[np.abs(pm - 0.5) < thr] = cf.TAKEOVER
        return dec

    def ens_defer(split, d):
        pm, ps = preds["LCSA"][split]
        _, psc = preds["LCSA"]["c2"]
        thr = np.quantile(psc, 1 - tk_rate_cal)
        dec = np.where(pm >= 0.5, cf.AVOID, cf.PROCEED).astype(np.int8)
        dec[ps > thr] = cf.TAKEOVER
        return dec

    scrc_apply, _, _ = coral(kappa=0.0, stratified=False, workload=False)

    def coral_L(fleet=FLEET, budget_override=None, gamma=GAMMA):
        ap_b, lo, hi_b = coral(budget_override=budget_override)
        dec2 = ap_b("c2", c2)
        sim2 = simulate(dec2, c2["y"], c2["tcpa_true"], c2["est_tcpa"], c2["bw"], c2["rtt"],
                        np.random.default_rng(seed * 7 + 5), priority="urgency", **fleet)
        late = cf.late_proxy(c2["tcpa_true"], c2["est_tcpa"], c2["bw"], c2["rtt"], sim2["wait_q90"], TAU_H_Q)
        pm2, ps2 = preds["LCSA"]["c2"]
        r2 = cf.score(pm2, ps2, KAPPA)
        hi = cf.calibrate_hi_lateness(r2, c2["y"], c2["link"], lo, hi_b, late, gamma, GRID)

        def apply(split, d):
            pm, ps = preds["LCSA"][split]
            return cf.decide(cf.score(pm, ps, KAPPA), d["link"], lo, hi)
        return apply, lo, hi, sim2["wait_q90"]

    L_apply, L_lo, L_hi, L_wq = coral_L()

    # Learn-then-Test (RCIP-style) joint control of miss and help rate, global thresholds
    mean_budget = float(np.dot([np.mean(c2["link"] == g) for g in sorted(budgets)], [budgets[g] for g in sorted(budgets)]))
    rc = np.r_[preds["LCSA"]["c1"][0], preds["LCSA"]["c2"][0]]
    yc = np.r_[c1["y"], c2["y"]]
    (ltt_lo, ltt_hi), ltt_N = cf.ltt_thresholds(rc, yc, ALPHA, mean_budget, delta=0.1)

    def ltt_apply(split, d):
        pm, _ = preds["LCSA"][split]
        dec = np.full(len(pm), cf.AVOID, np.int8)
        dec[pm < ltt_hi] = cf.TAKEOVER
        dec[pm < ltt_lo] = cf.PROCEED
        return dec

    methods = {
        "Rule-CPA": (lambda split, d: rule_scores(d), "urgency"),
        "Threshold-0.5": (threshold_only, "fcfs"),
        "Selective-conf": (selective_conf, "fcfs"),
        "Ensemble-defer": (ens_defer, "fcfs"),
        "SCRC-global": (scrc_apply, "fcfs"),
        "LTT-help (RCIP-style)": (ltt_apply, "fcfs"),
        "CORAL (ours)": (ours_apply, "urgency"),
        "CORAL-L (ours)": (L_apply, "urgency"),
    }
    ablations = {
        "w/o epistemic inflation": (coral(kappa=0.0)[0], "urgency"),
        "w/o link stratification": (coral(stratified=False)[0], "urgency"),
        "w/o workload budget": (coral(workload=False)[0], "urgency"),
        "w/o urgency queue": (ours_apply, "fcfs"),
        "w/o attention (MLP-set)": (coral(net="MLP-set")[0], "urgency"),
        "w/o context query": (coral(net="LCSA-noctx")[0], "urgency"),
        "w/o ensemble (single)": (coral(net="LCSA-single")[0], "urgency"),
    }

    def evaluate(apply, prio, split, d, sim_seed):
        dec = apply(split, d)
        res = simulate(dec, d["y"], d["tcpa_true"], d["est_tcpa"], d["bw"], d["rtt"],
                       np.random.default_rng(sim_seed), priority=prio, **FLEET)
        return res, dec

    for name, (ap, prio) in {**methods, **ablations}.items():
        res, dec = evaluate(ap, prio, "te", te, seed * 7 + 1)
        R["methods"][name] = res
        for s in ood:
            R["ood"].setdefault(name, {})[s] = evaluate(ap, prio, s, ood[s], seed * 7 + 2)[0]

    # ---- per-sample unsafe arrays (hazards only) for paired bootstrap ----
    hz = te["y"] == 1
    boot = {}
    for name in ["SCRC-global", "LTT-help (RCIP-style)", "CORAL (ours)", "CORAL-L (ours)"]:
        ap, prio = methods[name]
        res = simulate(ap("te", te), te["y"], te["tcpa_true"], te["est_tcpa"], te["bw"], te["rtt"],
                       np.random.default_rng(seed * 7 + 1), priority=prio, return_arrays=True, **FLEET)
        boot[name] = res["_unsafe"][hz].astype(np.int8)
    np.savez_compressed(os.path.join(out, f"seed{seed}_boot.npz"), **{k.split(" ")[0]: v for k, v in boot.items()})
    R["ltt"] = dict(lo=float(ltt_lo), hi=float(ltt_hi), N=int(ltt_N), beta=mean_budget)

    # ---- validity of the lateness proxy (assumption of Corollary 1) ----
    R["proxy"] = {}
    for split, d in [("te", te), ("ais_dropout", ood["ais_dropout"])]:
        dec = ours_apply(split, d)
        res = simulate(dec, d["y"], d["tcpa_true"], d["est_tcpa"], d["bw"], d["rtt"],
                       np.random.default_rng(seed * 7 + 6), priority="urgency", return_arrays=True, **FLEET)
        actual = res["_late"]
        proxy = cf.late_proxy(d["tcpa_true"], d["est_tcpa"], d["bw"], d["rtt"], L_wq, TAU_H_Q) & (d["y"] == 1) & (dec == cf.TAKEOVER)
        R["proxy"][split] = dict(n_actual_late=int(actual.sum()), n_proxy=int(proxy.sum()),
                                 caught=int((actual & proxy).sum()))

    # ---- calibration-set size sweep (validity and threshold variance) ----
    R["calsize"] = {}
    pm1, ps1 = preds["LCSA"]["c1"]; r1 = cf.score(pm1, ps1, KAPPA)
    pmt, pst = preds["LCSA"]["te"]; rt = cf.score(pmt, pst, KAPPA)
    rs = np.random.default_rng(seed + 77)
    for n1 in [250, 500, 1000, 2000, 4000, 6000]:
        miss, lams, viol = [], [], []
        for rep in range(30 if n1 < 6000 else 1):
            idx = rs.choice(len(r1), size=n1, replace=False) if n1 < len(r1) else np.arange(len(r1))
            lo = cf.calibrate_lo(r1[idx], c1["y"][idx], c1["link"][idx], ALPHA, GRID, stratified=True)
            dlo = np.array([lo.get(g, 0.0) for g in te["link"]])
            per = [float(np.mean(rt[(te["y"] == 1) & (te["link"] == g)] < lo.get(g, 0.0))) for g in range(3)]
            m = float(np.mean(rt[hz] < dlo[hz]))
            miss.append(m); lams.append([lo.get(g, 0.0) for g in range(3)]); viol.append(per)
        R["calsize"][n1] = dict(miss_mean=float(np.mean(miss)), miss_sd=float(np.std(miss)),
                                frac_above=float(np.mean(np.array(miss) > ALPHA)),
                                lam_sd=np.std(lams, 0).tolist(), lam_mean=np.mean(lams, 0).tolist(),
                                per_group_mean=np.mean(viol, 0).tolist())

    # per-link validity of the auto-clear guarantee (test, CORAL vs global)
    for name, ap in [("CORAL (ours)", ours_apply), ("w/o link stratification", ablations["w/o link stratification"][0])]:
        dec = ap("te", te)
        R["group_validity"][name] = {int(g): float(np.mean(dec[(te["link"] == g) & (te["y"] == 1)] == cf.PROCEED))
                                     for g in range(3)}
    R["thresholds_L"] = {int(k): float(v) for k, v in L_hi.items()}
    R["wait_q90_cal"] = float(L_wq)
    R["thresholds"] = {"lo": {int(k): float(v) for k, v in ours_lo.items()},
                       "hi": {int(k): float(v) for k, v in ours_hi.items()}}

    # ---------------- sweeps ----------------
    R["sweeps"]["alpha"] = {}
    for a in [0.005, 0.01, 0.02, 0.05, 0.10]:
        ap, _, _ = coral(alpha=a)
        dec = ap("te", te)
        R["sweeps"]["alpha"][a] = dict(
            miss=float(np.mean(dec[te["y"] == 1] == cf.PROCEED)),
            takeover=float(np.mean(dec == cf.TAKEOVER)),
            false_man=float(np.mean(dec[te["y"] == 0] == cf.AVOID)))
    R["sweeps"]["kappa"] = {}
    for k in [0.0, 0.5, 1.0, 2.0, 3.0]:
        ap, _, _ = coral(kappa=k)
        res, _ = evaluate(ap, "urgency", "te", te, seed * 7 + 1)
        res_o, _ = evaluate(ap, "urgency", "rough_sea", ood["rough_sea"], seed * 7 + 2)
        R["sweeps"]["kappa"][k] = dict(id=res, rough_sea=res_o)
    R["sweeps"]["gamma"] = {}
    for gm in [0.0025, 0.005, 0.01, 0.02]:
        apg = coral_L(gamma=gm)[0]
        R["sweeps"]["gamma"][gm] = evaluate(apg, "urgency", "te", te, seed * 7 + 1)[0]
    R["sweeps"]["operators"] = {}
    for m in [1, 2, 3, 4]:
        fl = dict(FLEET, M_ops=m)
        bud = cf.workload_budgets(c2["link"], c2["bw"], c2["rtt"], **fl)
        out_m = {}
        for lab, wl in [("workload", True), ("uniform", False)]:
            if wl:
                ap, _, _ = coral(budget_override=bud)
            else:
                w = np.array([np.mean(c2["link"] == g) for g in sorted(bud)])
                ub = cf.uniform_budgets(c2["link"], float(np.dot(w, [bud[g] for g in sorted(bud)])))
                ap, _, _ = coral(budget_override=ub)
            dec = ap("te", te)
            out_m[lab] = simulate(dec, te["y"], te["tcpa_true"], te["est_tcpa"], te["bw"], te["rtt"],
                                  np.random.default_rng(seed * 7 + 3), priority="urgency", **fl)
        apL = coral_L(fleet=fl, budget_override=bud)[0]
        decL = apL("te", te)
        out_m["lateness"] = simulate(decL, te["y"], te["tcpa_true"], te["est_tcpa"], te["bw"], te["rtt"],
                                     np.random.default_rng(seed * 7 + 3), priority="urgency", **fl)
        R["sweeps"]["operators"][m] = out_m

    # ---------------- online adaptation under shift ----------------
    # stream: 6000 ID test samples followed by 8000 rough-sea + AIS-dropout samples
    sh = generate(8000, np.random.default_rng(seed + 999), "test", sea=(0.7, 1.0), ais_drop=0.5)
    sh.pop("natural_hazard_rate", None)
    psh = nets["LCSA"].predict(sh["X"], sh["M"], sh["C"])
    pm_s = np.r_[preds["LCSA"]["te"][0][:6000], psh[0]]
    ps_s = np.r_[preds["LCSA"]["te"][1][:6000], psh[1]]
    y_s = np.r_[te["y"][:6000], sh["y"]]
    g_s = np.r_[te["link"][:6000], sh["link"]]
    r_s = cf.score(pm_s, ps_s, KAPPA)
    delay = 50
    tc_s = np.r_[te["tcpa_true"][:6000], sh["tcpa_true"]]
    et_s = np.r_[te["est_tcpa"][:6000], sh["est_tcpa"]]
    bw_s = np.r_[te["bw"][:6000], sh["bw"]]
    rt_s = np.r_[te["rtt"][:6000], sh["rtt"]]
    traces = {}
    variants = [("static", False, False, ours_lo, ours_hi), ("online", True, False, ours_lo, ours_hi),
                ("static_L", False, False, L_lo, L_hi), ("online_L", True, False, L_lo, L_hi),
                ("online_L_budget", True, True, L_lo, L_hi)]
    for lab, online, budget_on, lo0, hi0 in variants:
        oc = cf.OnlineCRC(lo0, ALPHA, eta=0.02)
        ob = cf.OnlineBudget(hi0, budgets, eta=0.002)
        dec = np.zeros(len(y_s), np.int8)
        upd_err = {g: [] for g in range(3)}
        for t in range(len(y_s)):
            g = g_s[t]
            lo = oc.lam[g] if online else lo0[g]
            hi = max(ob.lam[g] if budget_on else hi0[g], lo)
            dec[t] = cf.PROCEED if r_s[t] < lo else (cf.TAKEOVER if r_s[t] < hi else cf.AVOID)
            if budget_on:
                ob.update(g, dec[t] == cf.TAKEOVER, lo)
            if online and t - delay >= 0:
                u = t - delay
                if y_s[u] == 1:
                    upd_err[g_s[u]].append(float(r_s[u] < oc.lam[g_s[u]]))
                oc.update(g_s[u], r_s[u], y_s[u])
        miss = (dec == cf.PROCEED) & (y_s == 1)
        bound_rec = {}
        for g in range(3):
            Tg = len(upd_err[g]); Ng = int(np.sum(g_s == g))
            bound_rec[g] = dict(T_haz=Tg, upd_err=float(np.mean(upd_err[g])) if Tg else None,
                                bound_lo=cf.online_bound(0.02, Tg),
                                decision_miss=float(np.mean(miss[(g_s == g) & (y_s == 1)])) if Tg else None,
                                takeover=float(np.mean(dec[g_s == g] == cf.TAKEOVER)), beta=float(budgets[g]),
                                bound_hi=cf.online_bound(0.002, Ng))
        w = 1000
        roll = []
        for s0 in range(0, len(y_s) - w + 1, 250):
            hz = y_s[s0:s0 + w] == 1
            roll.append(float(miss[s0:s0 + w][hz].mean()) if hz.any() else 0.0)
        post = slice(6000, None)
        fl_post = simulate(dec[post], y_s[post], tc_s[post], et_s[post], bw_s[post], rt_s[post],
                           np.random.default_rng(seed * 7 + 4), priority="urgency", **FLEET)
        traces[lab] = dict(roll=roll,
                           miss_post=float(miss[6000:][y_s[6000:] == 1].mean()),
                           takeover_post=float(np.mean(dec[6000:] == cf.TAKEOVER)),
                           miss_pre=float(miss[:6000][y_s[:6000] == 1].mean()),
                           fleet_post=fl_post, bounds=bound_rec)
    R["online"] = traces
    R["runtime_s"] = time.time() - t0

    # timing of inference (per assessment, single core)
    x1 = te["X"][:2000]; m1 = te["M"][:2000]; cc = te["C"][:2000]
    t1 = time.time(); nets["LCSA"].predict(x1, m1, cc); R["latency_ms_per_assessment"] = (time.time() - t1) / 2000 * 1000

    # save a few arrays for figures (seed 0 only)
    if seed == 0:
        np.savez_compressed(os.path.join(out, "seed0_arrays.npz"),
                            y=te["y"], p=preds["LCSA"]["te"][0], s=preds["LCSA"]["te"][1],
                            p_mlp=preds["MLP-set"]["te"][0], link=te["link"],
                            p_rough=preds["LCSA"]["rough_sea"][0], y_rough=ood["rough_sea"]["y"],
                            s_rough=preds["LCSA"]["rough_sea"][1])
    with open(os.path.join(out, f"seed{seed}.json"), "w") as f:
        json.dump(R, f, indent=1, default=float)
    print(f"[seed {seed}] done {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="results")
    ap.add_argument("--source", default="sim", choices=["sim", "ais"])
    a = ap.parse_args()
    SOURCE = a.source
    if SOURCE == "ais":
        D_SAFE = 500.0
    os.makedirs(a.out, exist_ok=True)
    run(a.seed, a.out)
