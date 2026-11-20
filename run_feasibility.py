"""
CORAL-F experiments (post hoc on the saved LCSA predictions of run_experiments.py; no retraining).
usage: python run_feasibility.py --res results --seed 0
Re-derives SCRC-global / CORAL / CORAL-L thresholds exactly as in run_experiments.py, then
evaluates CORAL-F (static and online certificates) on the ID test set and the shifted sets.
"""
import argparse, json, os
import numpy as np
from coral import conformal as cf
from coral.feasibility import simulate_f, calibrate_certificate

GRID = np.linspace(0.0, 1.0, 2001)
ALPHA, KAPPA, GAMMA = 0.02, 1.0, 0.005
FLEET = dict(K=24, M_ops=2, r_e=1 / 60.0)
TAU_H_Q = 20.0 * np.exp(0.4 * 1.2816)


def load(res, seed):
    z = np.load(os.path.join(res, f"seed{seed}_preds.npz"))
    D = {}
    for k in z.files:
        s, f = k.split("__")
        D.setdefault(s, {})[f] = z[k]
    return D


def run(res, seed):
    D = load(res, seed)
    c1, c2, te = D["c1"], D["c2"], D["te"]
    shifts = [s for s in ("ais_dropout", "link_degradation", "rough_sea") if s in D]
    r = {s: cf.score(D[s]["pm"], D[s]["ps"], KAPPA) for s in D}
    budgets = cf.workload_budgets(c2["link"], c2["bw"], c2["rtt"], **FLEET)
    lo = cf.calibrate_lo(r["c1"], c1["y"], c1["link"], ALPHA, GRID, stratified=True)
    hi = cf.calibrate_hi(r["c2"], c2["link"], lo, budgets, GRID)
    # SCRC-global
    r0 = {s: cf.score(D[s]["pm"], D[s]["ps"], 0.0) for s in D}
    lo0 = cf.calibrate_lo(r0["c1"], c1["y"], c1["link"], ALPHA, GRID, stratified=False)
    hi0 = cf.calibrate_hi(r0["c2"], c2["link"], lo0, budgets, GRID) if False else None
    w = np.array([np.mean(c2["link"] == g) for g in sorted(budgets)])
    ub = cf.uniform_budgets(c2["link"], float(np.dot(w, [budgets[g] for g in sorted(budgets)])))
    hi0 = cf.calibrate_hi(r0["c2"], c2["link"], lo0, ub, GRID)
    # CORAL-L
    dec2 = cf.decide(r["c2"], c2["link"], lo, hi)
    from coral.fleet import simulate
    sim2 = simulate(dec2, c2["y"], c2["tcpa_true"], c2["est_tcpa"], c2["bw"], c2["rtt"],
                    np.random.default_rng(seed * 7 + 5), priority="urgency", **FLEET)
    late = cf.late_proxy(c2["tcpa_true"], c2["est_tcpa"], c2["bw"], c2["rtt"], sim2["wait_q90"], TAU_H_Q)
    hiL = cf.calibrate_hi_lateness(r["c2"], c2["y"], c2["link"], lo, hi, late, GAMMA, GRID)

    decide = {
        "SCRC-global": lambda s: cf.decide(r0[s], D[s]["link"], lo0, hi0),
        "CORAL": lambda s: cf.decide(r[s], D[s]["link"], lo, hi),
        "CORAL-L": lambda s: cf.decide(r[s], D[s]["link"], lo, hiL),
    }
    prio = {"SCRC-global": "fcfs", "CORAL": "urgency", "CORAL-L": "urgency"}
    # CORAL-F: policy-consistent certificate calibration on D2 under CORAL decisions
    cert = calibrate_certificate(dec2, c2, seed * 7 + 5, gamma=GAMMA, fleet=FLEET)
    cert_nb = calibrate_certificate(dec2, c2, seed * 7 + 5, gamma=GAMMA, fleet=FLEET, n_bins=1)
    cert_sw = calibrate_certificate(dec2, c2, seed * 7 + 5, gamma=GAMMA, fleet=FLEET, static_wait=sim2["wait_q90"])
    VAR = {  # name: (base decisions, certificate, mode, online)
        "SCRC-global": ("SCRC-global", None, "route", False),
        "CORAL": ("CORAL", None, "route", False),
        "CORAL-L": ("CORAL-L", None, "route", False),
        "CORAL-F": ("CORAL", cert, "full", False),
        "CORAL-F-online": ("CORAL", cert, "full", True),
        "F w/o routing (cert. timeout only)": ("CORAL", cert, "timeout", False),
        "F w/o cert. timeout (routing only)": ("CORAL", cert, "route", False),
        "F w/o live queue state": ("CORAL", cert_sw, "full", False),
        "F w/o Mondrian deadline bins": ("CORAL", cert_nb, "full", False),
    }

    def ev(name, s, sim_seed, **kw):
        d = D[s]
        base, c, mode, onl = VAR[name]
        return simulate_f(decide[base](s), d["y"], d["tcpa_true"], d["est_tcpa"], d["bw"], d["rtt"],
                          np.random.default_rng(sim_seed), priority=prio[base], cert=c, mode=mode,
                          online=onl, **FLEET, **kw)

    names = list(VAR)
    R = dict(seed=seed, cert={k: (v if isinstance(v, list) else float(v)) for k, v in cert.items() if v is not None},
             methods={}, shift={}, audit={})
    for nm in names:
        R["methods"][nm] = ev(nm, "te", seed * 7 + 1)
        for s in shifts:
            R["shift"].setdefault(nm, {})[s] = ev(nm, s, seed * 7 + 2)
    # matched-cost frontier: CORAL vs CORAL-F over alpha
    R["frontier"] = {}
    for al in (0.005, 0.01, 0.015, 0.02, 0.03, 0.04):
        lo_a = cf.calibrate_lo(r["c1"], c1["y"], c1["link"], al, GRID, stratified=True)
        hi_a = cf.calibrate_hi(r["c2"], c2["link"], lo_a, budgets, GRID)
        dec2a = cf.decide(r["c2"], c2["link"], lo_a, hi_a)
        cert_a = calibrate_certificate(dec2a, c2, seed * 7 + 5, gamma=GAMMA, fleet=FLEET)
        for s in ["te"] + (["ais_dropout"] if "ais_dropout" in D else []):
            d = D[s]; dec = cf.decide(r[s], d["link"], lo_a, hi_a)
            sd = seed * 7 + (1 if s == "te" else 2)
            for nm, c in (("CORAL", None), ("CORAL-F", cert_a)):
                o = simulate_f(dec, d["y"], d["tcpa_true"], d["est_tcpa"], d["bw"], d["rtt"],
                               np.random.default_rng(sd), cert=c, mode="full", **FLEET)
                R["frontier"].setdefault(s, {}).setdefault(nm, []).append(
                    dict(alpha=al, unsafe=o["unsafe_rate"], totM=o["total_manoeuvre"], FM=o["false_manoeuvre"]))
    # audit: does the certificate (no routing) flag the hazards that actually end up late?
    for s in ["te"] + shifts:
        d = D[s]
        for mode in ("static", "online"):
            a = simulate_f(decide["CORAL"](s), d["y"], d["tcpa_true"], d["est_tcpa"], d["bw"], d["rtt"],
                           np.random.default_rng(seed * 7 + (1 if s == "te" else 2)), cert=cert, route=False, mode="full",
                           online=(mode == "online"), return_arrays=True, **FLEET)
            lt = a["_late"]
            R["audit"].setdefault(s, {})[mode] = dict(n_late=int(lt.sum()), caught=int((lt & a["_flag"]).sum()),
                                                      flagged=int(a["_flag"].sum()))
    # paired per-hazard unsafe indicators on ID test, for bootstrap
    hz = te["y"] == 1
    boot = {}
    for nm in ("SCRC-global", "CORAL", "CORAL-L", "CORAL-F"):
        o = ev(nm, "te", seed * 7 + 1, return_arrays=True)
        boot[nm] = o["_unsafe"][hz].astype(np.int8)
    np.savez_compressed(os.path.join(res, f"seed{seed}_fboot.npz"), **boot)
    # shift stream: ID test followed by AIS dropout, static vs online certificate
    if "ais_dropout" in D:
        S = {k: np.r_[te[k], D["ais_dropout"][k]] for k in ("y", "tcpa_true", "est_tcpa", "bw", "rtt", "link")}
        rs = np.r_[r["te"], r["ais_dropout"]]
        dec = cf.decide(rs, S["link"], lo, hi)
        nID = len(te["y"])
        R["stream"] = {}
        for mode in ("static", "online"):
            o = simulate_f(dec, S["y"], S["tcpa_true"], S["est_tcpa"], S["bw"], S["rtt"],
                           np.random.default_rng(seed * 7 + 9), cert=cert, mode="full", online=(mode == "online"),
                           return_arrays=True, **FLEET)
            post = np.zeros(len(dec), bool); post[nID:] = True
            hzp = post & (S["y"] == 1)
            R["stream"][mode] = dict(unsafe_post=float(o["_unsafe"][hzp].mean()),
                                     late_post=float(o["_late"][hzp].mean()),
                                     fm_post=float(((S["y"] == 0) & post & (o["_dec"] == cf.AVOID)).sum() / max(1, ((S["y"] == 0) & post).sum())),
                                     unsafe_all=o["unsafe_rate"])
            if mode == "online" and seed == 0:
                np.savez_compressed(os.path.join(res, "seed0_fstream.npz"), qD=o["_qD_trace"], qR=o["_qR_trace"])
    with open(os.path.join(res, f"seed{seed}_feas.json"), "w") as f:
        json.dump(R, f, indent=1, default=float)
    return R


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", default="results")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    R = run(a.res, a.seed)
    m = R["methods"]
    print(a.res, a.seed, "cert", R["cert"])
    for k, v in m.items():
        print(f"  {k:16s} unsafe {100*v['unsafe_rate']:.2f} late {100*v['late_takeover_hazard']:.2f} "
              f"FM {100*v['false_manoeuvre']:.1f} totM {100*v['total_manoeuvre']:.1f} TK {100*v['takeover_rate']:.1f} "
              f"covR {v.get('cov_R', float('nan')):.3f} covD {v.get('cov_D', float('nan')):.3f}")
    for nm, ss in R["shift"].items():
        print("  ", nm, {s: (round(100*v['unsafe_rate'], 2), round(100*v['late_takeover_hazard'], 2), round(100*v['false_manoeuvre'], 1)) for s, v in ss.items()})
    print("  audit", R["audit"]); print("  stream", R.get("stream"))
