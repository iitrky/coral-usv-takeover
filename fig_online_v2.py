import glob, json, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8.5})
Rs = [json.load(open(f)) for f in sorted(glob.glob(f"{__import__('sys').argv[1] if len(__import__('sys').argv)>1 else 'results'}/seed[0-9].json"))]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.4, 2.9), gridspec_kw=dict(width_ratios=[1.5, 1]))
for v, c, lab in [("static_L", "#d9822b", "static thresholds"), ("online_L", "#1b3f73", "online $\\lambda_{lo}$ (Eq. 25)")]:
    tr = np.array([R["online"][v]["roll"] for R in Rs]) * 100
    t = np.arange(tr.shape[1]) * 250 + 500
    a1.plot(t, tr.mean(0), color=c, label=lab); a1.fill_between(t, tr.mean(0) - tr.std(0), tr.mean(0) + tr.std(0), color=c, alpha=0.15)
a1.axvline(6000, color="#555", ls=":", lw=1); a1.text(6150, 5.6, "shift onset", fontsize=7.5)
a1.axhline(2, color="#999", ls="--", lw=0.8); a1.text(200, 2.15, "$\\alpha$ = 2%", fontsize=7.5)
a1.set_xlabel("assessment index in stream"); a1.set_ylabel("rolling auto-clear miss (%)"); a1.legend(frameon=False, fontsize=7.5)
a1.set_title("(a) safety threshold", loc="left", fontsize=8.5)
vs = [("static", "CORAL\nstatic"), ("static_L", "CORAL-L\nstatic"), ("online_L", "CORAL-L\nonline $\\lambda_{lo}$"), ("online_L_budget", "CORAL-L\nonline both")]
x = np.arange(len(vs)); w = 0.38
for j, (k, c, lab) in enumerate([("unsafe_rate", "#b8433b", "unsafe"), ("late_takeover_hazard", "#8a96a3", "late takeover")]):
    v = np.array([[R["online"][n]["fleet_post"][k] for n, _ in vs] for R in Rs]) * 100
    a2.bar(x + (j - 0.5) * w, v.mean(0), w, yerr=v.std(0), color=c, label=lab, capsize=2, error_kw=dict(lw=0.6))
a2.set_xticks(x); a2.set_xticklabels([l for _, l in vs], fontsize=6.8); a2.set_ylabel("% of hazards after shift")
a2.legend(frameon=False, fontsize=7.5); a2.set_title("(b) fleet outcome after shift", loc="left", fontsize=8.5)
for a in (a1, a2): a.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig((("figures_" + __import__("sys").argv[1].replace("results_","")) if len(__import__("sys").argv)>1 else "figures") + "/fig8_online_fleet.png", dpi=300)
