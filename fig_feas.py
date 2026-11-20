"""Fig. 12: matched-cost frontiers CORAL vs CORAL-F; Fig. 13: lateness recall, proxy vs certificate."""
import json, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
plt.rcParams.update({"font.size": 9, "font.family": "serif", "axes.spines.top": False, "axes.spines.right": False})
C = {"CORAL": "#7a7a7a", "CORAL-F": "#1f5aa6"}
S = {r: json.load(open(f"{r}/feas_summary.json")) for r in ("results", "results_ais")}
fig, ax = plt.subplots(1, 4, figsize=(11, 2.8))
k = 0
for r, lab in (("results", "Sandbox"), ("results_ais", "AIS replay")):
    for sp, sl in (("te", "in distribution"), ("ais_dropout", "AIS dropout")):
        a = ax[k]; k += 1
        for nm in ("CORAL", "CORAL-F"):
            pts = np.array([(p[2], p[1]) for p in S[r]["frontier"][sp][nm]])
            a.plot(pts[:, 0], pts[:, 1], "-o", ms=3.5, color=C[nm], label=nm if nm == "CORAL" else "CORAL-F (ours)")
            i2 = [p[0] for p in S[r]["frontier"][sp][nm]].index(0.02)
            a.plot(pts[i2, 0], pts[i2, 1], "s", ms=6, mfc="none", color=C[nm])
        a.axhline(2.0, ls=":", lw=0.8, color="k")
        a.set_title(f"({'abcd'[k-1]}) {lab}, {sl}", fontsize=9)
        a.set_xlabel("Total manoeuvres on non-hazards (%)")
        if k == 1: a.set_ylabel("Unsafe rate among hazards (%)")
ax[0].legend(frameon=False, fontsize=8)
plt.tight_layout(); plt.savefig("figures/fig12_feas_frontier.png", dpi=300)

fig, ax = plt.subplots(figsize=(7.5, 2.5))
cert = {r: [100 * S[r]["audit"][s]["caught"] / max(1, S[r]["audit"][s]["n_late"]) for s in ("te", "ais_dropout")] for r in S}
proxy = {"results": [84, 21], "results_ais": [70, 1]}
x = np.arange(4); w = 0.38
lab = ["Sandbox ID", "Sandbox dropout", "AIS ID", "AIS dropout"]
pv = proxy["results"] + proxy["results_ais"]; cv = cert["results"] + cert["results_ais"]
ax.bar(x - w / 2, pv, w, color="#bdbdbd", label="CORAL-L proxy (Eq. 26)")
ax.bar(x + w / 2, cv, w, color="#1f5aa6", label="CORAL-F certificate (Eq. 35)")
for i in range(4):
    ax.text(x[i] - w / 2, pv[i] + 2, f"{pv[i]:.0f}", ha="center", fontsize=7)
    ax.text(x[i] + w / 2, cv[i] + 2, f"{cv[i]:.0f}", ha="center", fontsize=7)
ax.set_xticks(x); ax.set_xticklabels(lab, fontsize=8); ax.set_ylim(0, 112)
ax.set_ylabel("Late takeovers flagged (%)"); ax.legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(1.01, 1.0))
plt.tight_layout(); plt.savefig("figures/fig13_feas_recall.png", dpi=300)
print(cv)
