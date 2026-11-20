"""Safety / false-manoeuvre trade-off curves (Pareto frontiers) from saved predictions.
For each target alpha, every method is recalibrated and evaluated on the fleet simulator.
usage: python frontier.py results_v3 [results_ais2 ...]
"""
import glob, json, sys
import numpy as np
from coral import conformal as cf
from coral.fleet import simulate

ALPHAS = [0.003, 0.005, 0.0075, 0.01, 0.015, 0.02, 0.03, 0.05]
GRID = np.linspace(0.0, 1.0, 2001)
FLEET = dict(K=24, M_ops=2, r_e=1 / 60.0)
KAPPA, GAMMA = 1.0, 0.005
TAU_H_Q = 20.0 * np.exp(0.4 * 1.2816)


def split(P, name):
    return {k.split("__", 1)[1]: P[k] for k in P.files if k.startswith(name + "__")}


def fleet(dec, d, seed, prio):
    return simulate(dec, d["y"], d["tcpa_true"], d["est_tcpa"], d["bw"], d["rtt"],
                    np.random.default_rng(seed * 7 + 1), priority=prio, **FLEET)


def decide(r, link, lo, hi):
    return cf.decide(r, link, lo, hi)


def run_seed(path, seed):
    P = np.load(path)
    c1, c2, te = split(P, "c1"), split(P, "c2"), split(P, "te")
    bud = cf.workload_budgets(c2["link"], c2["bw"], c2["rtt"], **FLEET)
    w = np.array([np.mean(c2["link"] == g) for g in sorted(bud)])
    mean_b = float(np.dot(w, [bud[g] for g in sorted(bud)]))
    uni = cf.uniform_budgets(c2["link"], mean_b)
    r1, r2, rt = (d["pm"] + KAPPA * d["ps"] for d in (c1, c2, te))
    out = {}
    for a in ALPHAS:
        res = {}
        # CORAL and CORAL-L
        lo = cf.calibrate_lo(r1, c1["y"], c1["link"], a, GRID)
        hi = cf.calibrate_hi(r2, c2["link"], lo, bud, GRID)
        res["CORAL"] = fleet(decide(rt, te["link"], lo, hi), te, seed, "urgency")
        s2 = fleet(decide(r2, c2["link"], lo, hi), c2, seed + 100, "urgency")
        late = cf.late_proxy(c2["tcpa_true"], c2["est_tcpa"], c2["bw"], c2["rtt"], s2["wait_q90"], TAU_H_Q)
        hiL = cf.calibrate_hi_lateness(r2, c2["y"], c2["link"], lo, hi, late, GAMMA, GRID)
        res["CORAL-L"] = fleet(decide(rt, te["link"], lo, hiL), te, seed, "urgency")
        # SCRC-global (kappa = 0, pooled, uniform budget, FCFS)
        q1, q2, qt = c1["pm"], c2["pm"], te["pm"]
        lo_g = cf.calibrate_lo(q1, c1["y"], c1["link"], a, GRID, stratified=False)
        hi_g = cf.calibrate_hi(q2, c2["link"], lo_g, uni, GRID)
        res["SCRC-global"] = fleet(decide(qt, te["link"], lo_g, hi_g), te, seed, "fcfs")
        # LTT (RCIP-style): high-probability joint control
        (l, h), _ = cf.ltt_thresholds(np.r_[q1, q2], np.r_[c1["y"], c2["y"]], a, mean_b, delta=0.1)
        dec = np.full(len(qt), cf.AVOID, np.int8); dec[qt < h] = cf.TAKEOVER; dec[qt < l] = cf.PROCEED
        res["LTT-help"] = fleet(dec, te, seed, "fcfs")
        out[a] = {m: {k: v[k] for k in ("unsafe_rate", "auto_clear_miss", "false_manoeuvre", "takeover_rate", "utilisation", "mean_wait")}
                  for m, v in res.items()}
    return out


def interp_at(fm, un, target):
    o = np.argsort(fm)
    fm, un = np.asarray(fm)[o], np.asarray(un)[o]
    if target < fm[0] or target > fm[-1]:
        return np.nan
    return float(np.interp(target, fm, un))


if __name__ == "__main__":
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8.5})
    dirs = sys.argv[1:]
    fig, axes = plt.subplots(1, len(dirs), figsize=(3.7 * len(dirs), 3.0), squeeze=False)
    colors = {"SCRC-global": "#d9822b", "LTT-help": "#8a96a3", "CORAL": "#2f6db3", "CORAL-L": "#1b3f73"}
    lines = []
    for ax, RD in zip(axes[0], dirs):
        files = sorted(glob.glob(f"{RD}/seed[0-9]_preds.npz"))
        allr = [run_seed(f, int(f.split("seed")[1][0])) for f in files]
        json.dump({str(i): {str(a): v for a, v in r.items()} for i, r in enumerate(allr)}, open(f"{RD}/frontier.json", "w"))
        lines.append(f"## {RD}: unsafe rate (%) at matched false-manoeuvre rate (interpolated per seed, mean ± SD)")
        lines.append("| false manoeuvre | " + " | ".join(colors) + " |\n|---|" + "---|" * len(colors))
        for tgt in [0.10, 0.125, 0.15, 0.20]:
            row = []
            for m in colors:
                v = [interp_at([r[a][m]["false_manoeuvre"] for a in ALPHAS], [r[a][m]["unsafe_rate"] for a in ALPHAS], tgt) for r in allr]
                v = np.array(v) * 100
                row.append("n/a" if np.isnan(v).any() else f"{v.mean():.2f} ± {v.std(ddof=1):.2f}")
            lines.append(f"| {tgt*100:.1f}% | " + " | ".join(row) + " |")
        lines.append("\nper-alpha means (unsafe %, false man %, auto-clear miss %, util %):")
        for a in ALPHAS:
            lines.append(f"alpha={a}: " + "; ".join(
                f"{m} {np.mean([r[a][m]['unsafe_rate'] for r in allr])*100:.2f}/{np.mean([r[a][m]['false_manoeuvre'] for r in allr])*100:.1f}/"
                f"{np.mean([r[a][m]['auto_clear_miss'] for r in allr])*100:.2f}/{np.mean([r[a][m]['utilisation'] for r in allr])*100:.0f}" for m in colors))
        for m, c in colors.items():
            fm = np.array([[r[a][m]["false_manoeuvre"] for a in ALPHAS] for r in allr]) * 100
            un = np.array([[r[a][m]["unsafe_rate"] for a in ALPHAS] for r in allr]) * 100
            ax.errorbar(fm.mean(0), un.mean(0), xerr=fm.std(0), yerr=un.std(0), fmt="o-", ms=3, color=c, capsize=1.5, lw=1.2, elinewidth=0.6, label=m)
        ax.set_xlabel("false manoeuvre rate (%)"); ax.set_ylabel("unsafe rate among hazards (%)")
        ax.set_xlim(0, 45); ax.set_ylim(0, None)
        ax.set_title("(a) sandbox" if "ais" not in RD else "(b) real AIS traffic", loc="left", fontsize=8.5)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0][0].legend(frameon=False, fontsize=7.5)
    fig.tight_layout(); fig.savefig("figures/fig11_frontier.png", dpi=300)
    open("frontier_summary.md", "w").write("\n".join(lines))
    print("\n".join(lines))
