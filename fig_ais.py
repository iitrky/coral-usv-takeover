"""Fig. 9: real-traffic (AIS replay) summary."""
import glob, json, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8.5})
Rs = [json.load(open(f)) for f in sorted(glob.glob("results_ais/seed[0-9].json"))]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.4, 2.9))
for lab, c, mk, name in [("uniform", "#d9822b", "s", "uniform $\\beta$ (same mean)"), ("workload", "#2f6db3", "o", "CORAL"), ("lateness", "#1b3f73", "^", "CORAL-L")]:
    u = np.array([[R["sweeps"]["operators"][m][lab]["unsafe_rate"] for m in "1234"] for R in Rs]) * 100
    a1.errorbar([1, 2, 3, 4], u.mean(0), yerr=u.std(0, ddof=1), fmt=mk + "-", color=c, capsize=3, ms=4, label=name)
a1.set_xticks([1, 2, 3, 4]); a1.set_xlabel("operators M (K = 24 USVs)"); a1.set_ylabel("unsafe rate among hazards (%)")
a1.legend(frameon=False, fontsize=7.5); a1.set_title("(a) safety versus ROC capacity", loc="left", fontsize=8.5)
vs = [("static", "CORAL\nstatic"), ("static_L", "CORAL-L\nstatic"), ("online_L", "CORAL-L\nonline $\\lambda_{lo}$"), ("online_L_budget", "CORAL-L\nonline both")]
x = np.arange(len(vs)); w = 0.38
for j, (k, c, lab) in enumerate([("unsafe_rate", "#b8433b", "unsafe"), ("late_takeover_hazard", "#8a96a3", "late takeover")]):
    v = np.array([[R["online"][n]["fleet_post"][k] for n, _ in vs] for R in Rs]) * 100
    a2.bar(x + (j - 0.5) * w, v.mean(0), w, yerr=v.std(0, ddof=1), color=c, label=lab, capsize=2, error_kw=dict(lw=0.6))
a2.set_xticks(x); a2.set_xticklabels([l for _, l in vs], fontsize=6.8); 
a2.set_ylabel("% of hazards after shift"); a2.legend(frameon=False, fontsize=7.5, loc="upper right", bbox_to_anchor=(1.0, 1.0)); a2.set_ylim(0, 22)
a2.set_title("(b) fleet outcome after shift", loc="left", fontsize=8.5)
for a in (a1, a2): a.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig("figures_ais/fig9_ais_replay.png", dpi=300)
