"""Aggregate per-seed JSON results into tables (markdown/JSON) and result figures."""
import glob, json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import sys
RD = sys.argv[1] if len(sys.argv) > 1 else "results"
RES = sorted(glob.glob(f"{RD}/seed[0-9].json"))
Rs = [json.load(open(f)) for f in RES]
S = len(Rs)
OUT = "figures" if RD == "results" else "figures_" + RD.replace("results_", ""); os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8.5})
C = {"LTT-help (RCIP-style)": "#6b8e9f", "CORAL-L (ours)": "#1b3f73", "CORAL (ours)": "#2f6db3", "SCRC-global": "#d9822b", "Ensemble-defer": "#8a96a3",
     "Selective-conf": "#b0a36b", "Rule-CPA": "#b8433b", "Threshold-0.5": "#555555"}


def ms(vals, pct=True, d=2):
    v = np.array(vals, float) * (100 if pct else 1)
    return f"{v.mean():.{d}f} ± {v.std(ddof=1) if len(v) > 1 else 0:.{d}f}"


summary = {"n_seeds": S}
lines = []
# ---- predictor table
lines.append("## Table A Predictor quality (ID test)\n| Backbone | AUROC | AUPRC | Brier | ECE | NLL |\n|---|---|---|---|---|---|")
for b in ["LCSA", "MLP-set", "LCSA-noctx", "LCSA-single"]:
    row = [ms([R["predictor"][b]["test"][k] for R in Rs], pct=False, d=4) for k in ["auroc", "auprc", "brier", "ece", "nll"]]
    lines.append(f"| {b} | " + " | ".join(row) + " |")
# ---- main table
keys = [("unsafe_rate", "Unsafe %"), ("auto_clear_miss", "Auto-clear miss %"), ("late_takeover_hazard", "Late takeover %"),
        ("false_manoeuvre", "False manoeuvre %"), ("takeover_rate", "Takeover %"), ("mrm_rate", "MRM / takeover %"),
        ("utilisation", "Operator util. %"), ("mean_wait", "Mean wait s")]
main_methods = ["Threshold-0.5", "Rule-CPA", "Selective-conf", "Ensemble-defer", "SCRC-global", "LTT-help (RCIP-style)", "CORAL (ours)", "CORAL-L (ours)"]
main_methods = [m for m in main_methods if m in Rs[0]["methods"]]
abl = ["CORAL (ours)", "w/o epistemic inflation", "w/o link stratification", "w/o workload budget", "w/o urgency queue",
       "w/o attention (MLP-set)", "w/o context query", "w/o ensemble (single)"]
for title, mlist in [("Table B Main results (ID test, fleet K=24, M=2)", main_methods), ("Table C Ablation", abl)]:
    lines.append(f"\n## {title}\n| Method | " + " | ".join(k[1] for k in keys) + " |\n|" + "---|" * (len(keys) + 1))
    for m in mlist:
        row = [ms([R["methods"][m][k] for R in Rs], pct=(k != "mean_wait"), d=(1 if k == "mean_wait" else 2)) for k, _ in keys]
        lines.append(f"| {m} | " + " | ".join(row) + " |")
summary["methods"] = {m: {k: [R["methods"][m][k] for R in Rs] for k, _ in keys} for m in Rs[0]["methods"]}
# ---- OOD table
shifts = list(Rs[0]["ood"]["CORAL (ours)"].keys())
lines.append("\n## Table D Unsafe rate % under distribution shift\n| Method | " + " | ".join(shifts) + " |\n|" + "---|" * (len(shifts) + 1))
for m in [x for x in main_methods + ["w/o workload budget"] if x in Rs[0]["ood"]]:
    lines.append(f"| {m} | " + " | ".join(ms([R["ood"][m][s]["unsafe_rate"] for R in Rs]) for s in shifts) + " |")
lines.append("\n## Table D2 CORAL under shift: auto-clear miss %, takeover %, false manoeuvre %, AUROC\n| Shift | miss | takeover | false man. | AUROC |\n|---|---|---|---|---|")
for s in shifts:
    lines.append(f"| {s} | {ms([R['ood']['CORAL (ours)'][s]['auto_clear_miss'] for R in Rs])} | {ms([R['ood']['CORAL (ours)'][s]['takeover_rate'] for R in Rs])} | "
                 f"{ms([R['ood']['CORAL (ours)'][s]['false_manoeuvre'] for R in Rs])} | {ms([R['predictor']['LCSA'][s]['auroc'] for R in Rs], pct=False, d=4)} |")
lines.append("\n## Table E Epistemic OOD detection AUROC (sigma, ID vs shift)\n| " + " | ".join(shifts) + " |\n|" + "---|" * 5)
lines.append("| " + " | ".join(ms([R["ood_detect"][s] for R in Rs], pct=False, d=3) for s in shifts) + " |")
# ---- per-group validity
lines.append("\n## Table F Per-link auto-clear miss % among hazards (target alpha = 2%)\n| Method | LEO | GEO | DEG |\n|---|---|---|---|")
for m in ["CORAL (ours)", "w/o link stratification"]:
    lines.append(f"| {m} | " + " | ".join(ms([R["group_validity"][m][str(g)] for R in Rs]) for g in range(3)) + " |")
lines.append("\nbudgets beta_g: " + str({g: ms([R["budgets"][str(g)] for R in Rs]) for g in range(3)}))
lines.append("thresholds lo: " + str({g: ms([R["thresholds"]["lo"][str(g)] for R in Rs], pct=False, d=3) for g in range(3)}))
lines.append("thresholds hi: " + str({g: ms([R["thresholds"]["hi"][str(g)] for R in Rs], pct=False, d=3) for g in range(3)}))
# ---- kappa
lines.append("\n## Table G kappa sensitivity (ID unsafe %, ID false man %, rough-sea unsafe %)\n| kappa | ID unsafe | ID false man. | rough-sea unsafe |\n|---|---|---|---|")
for k in ["0.0", "0.5", "1.0", "2.0", "3.0"]:
    lines.append(f"| {k} | {ms([R['sweeps']['kappa'][k]['id']['unsafe_rate'] for R in Rs])} | {ms([R['sweeps']['kappa'][k]['id']['false_manoeuvre'] for R in Rs])} | {ms([R['sweeps']['kappa'][k]['rough_sea']['unsafe_rate'] for R in Rs])} |")
# ---- online
lines.append("\n## Table H Online adaptation (shift = rough sea + AIS dropout 0.5)\n| Variant | miss pre-shift | miss post-shift | takeover post-shift |\n|---|---|---|---|")
for v in ["static", "online"]:
    lines.append(f"| {v} | {ms([R['online'][v]['miss_pre'] for R in Rs])} | {ms([R['online'][v]['miss_post'] for R in Rs])} | {ms([R['online'][v]['takeover_post'] for R in Rs])} |")
lines.append(f"\ninference latency ms/assessment (5-member ensemble, numpy, 1 core): {ms([R['latency_ms_per_assessment'] for R in Rs], pct=False, d=3)}")
# ---- v2 extras
if "gamma" in Rs[0]["sweeps"]:
    lines.append("\n## Table I gamma sweep (CORAL-L)\n| gamma | unsafe | late | false man | takeover | util | MRM/tk |\n|---|---|---|---|---|---|---|")
    for gm in ["0.0025", "0.005", "0.01", "0.02"]:
        G = [R["sweeps"]["gamma"][gm] for R in Rs]
        lines.append(f"| {gm} | " + " | ".join(ms([x[k] for x in G]) for k in ["unsafe_rate", "late_takeover_hazard", "false_manoeuvre", "takeover_rate", "utilisation", "mrm_rate"]) + " |")
    lines.append("\n## Table J operators sweep\n| M | variant | unsafe | late | false man | takeover | MRM/h |\n|---|---|---|---|---|---|---|")
    for m in ["1", "2", "3", "4"]:
        for lab in ["uniform", "workload", "lateness"]:
            G = [R["sweeps"]["operators"][m][lab] for R in Rs]
            lines.append(f"| {m} | {lab} | " + " | ".join(ms([x[k] for x in G]) for k in ["unsafe_rate", "late_takeover_hazard", "false_manoeuvre", "takeover_rate"]) + f" | {ms([x['mrm_per_hour'] for x in G], pct=False, d=1)} |")
    lines.append("\n## Table K online stream, post-shift fleet metrics\n| variant | miss pre | miss post | unsafe post | late post | takeover post | util post | MRM/tk post |\n|---|---|---|---|---|---|---|---|")
    for v in ["static", "online", "static_L", "online_L", "online_L_budget"]:
        G = [R["online"][v] for R in Rs]
        lines.append(f"| {v} | {ms([x['miss_pre'] for x in G])} | {ms([x['miss_post'] for x in G])} | " + " | ".join(ms([x['fleet_post'][k] for x in G]) for k in ["unsafe_rate", "late_takeover_hazard", "takeover_rate", "utilisation", "mrm_rate"]) + " |")
    lines.append("\nthresholds_L hi: " + str({g: ms([R["thresholds_L"][str(g)] for R in Rs], pct=False, d=3) for g in range(3)}) + f"  wait_q90_cal: {ms([R['wait_q90_cal'] for R in Rs], pct=False, d=1)}")
lines.append(f"matched takeover rate: {ms([R['matched_takeover_rate'] for R in Rs])}")
None or open(f"{RD}/summary_tables.md", "w").write("\n".join(lines))
json.dump(summary, open(f"{RD}/summary.json", "w"), indent=1)
print("\n".join(lines))

# ================= figures =================
# Fig 4 reliability + score histogram (seed 0)
A = np.load(f"{RD}/seed0_arrays.npz")
fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.2, 2.8))
for p, y, lab, c in [(A["p"], A["y"], "ID test", "#2f6db3"), (A["p_rough"], A["y_rough"], "rough sea (shift)", "#b8433b")]:
    e = np.linspace(0, 1, 11); mid, acc = [], []
    for lo, hi in zip(e[:-1], e[1:]):
        s = (p >= lo) & (p < hi)
        if s.sum() > 30:
            mid.append(p[s].mean()); acc.append(y[s].mean())
    a1.plot(mid, acc, "o-", color=c, ms=3.5, label=lab)
a1.plot([0, 1], [0, 1], "--", color="#999", lw=0.8)
a1.set_xlabel("predicted hazard probability"); a1.set_ylabel("observed hazard frequency"); a1.legend(frameon=False)
a1.set_title("(a) reliability (seed 0)", loc="left", fontsize=8.5)
a2.hist(A["p"][A["y"] == 0], bins=40, alpha=0.6, color="#3a8f5c", label="no hazard", density=True)
a2.hist(A["p"][A["y"] == 1], bins=40, alpha=0.6, color="#b8433b", label="hazard", density=True)
a2.set_yscale("log"); a2.set_xlabel("ensemble mean $\\bar p$"); a2.legend(frameon=False)
a2.set_title("(b) score distribution", loc="left", fontsize=8.5)
for a in (a1, a2):
    a.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(f"{OUT}/fig4_calibration.png", dpi=300); plt.close(fig)

# Fig 5 alpha sweep
al = ["0.005", "0.01", "0.02", "0.05", "0.1"]
x = np.array([float(a) for a in al])
miss = np.array([[R["sweeps"]["alpha"][a]["miss"] for a in al] for R in Rs])
fm = np.array([[R["sweeps"]["alpha"][a]["false_man"] for a in al] for R in Rs])
fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.2, 2.8))
a1.errorbar(x * 100, miss.mean(0) * 100, yerr=miss.std(0) * 100, fmt="o-", color="#2f6db3", capsize=3, ms=4, label="empirical")
a1.plot(x * 100, x * 100, "--", color="#999", label="target $\\alpha$")
a1.set_xscale("log"); a1.set_yscale("log"); a1.set_xlabel("target $\\alpha$ (%)"); a1.set_ylabel("auto-clear miss among hazards (%)")
a1.legend(frameon=False); a1.set_title("(a) risk validity", loc="left", fontsize=8.5)
a2.errorbar(x * 100, fm.mean(0) * 100, yerr=fm.std(0) * 100, fmt="s-", color="#b8433b", capsize=3, ms=4)
a2.set_xscale("log"); a2.set_xlabel("target $\\alpha$ (%)"); a2.set_ylabel("false manoeuvre rate (%)")
a2.set_title("(b) price of safety", loc="left", fontsize=8.5)
for a in (a1, a2):
    a.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(f"{OUT}/fig5_alpha_sweep.png", dpi=300); plt.close(fig)

# Fig 6 operators sweep
Ms = ["1", "2", "3", "4"]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.2, 2.8))
labs6 = [("workload", "#2f6db3", "o"), ("uniform", "#d9822b", "s")] + ([("lateness", "#1b3f73", "^")] if "lateness" in Rs[0]["sweeps"]["operators"]["1"] else [])
for lab, c, mk in labs6:
    u = np.array([[R["sweeps"]["operators"][m][lab]["unsafe_rate"] for m in Ms] for R in Rs]) * 100
    mr = np.array([[R["sweeps"]["operators"][m][lab]["mrm_per_hour"] for m in Ms] for R in Rs])
    name = {"workload": "CORAL (workload $\\beta_g$)", "uniform": "uniform $\\beta$ (same mean)", "lateness": "CORAL-L (+ lateness bound)"}[lab]
    a1.errorbar([1, 2, 3, 4], u.mean(0), yerr=u.std(0), fmt=mk + "-", color=c, capsize=3, ms=4, label=name)
    a2.errorbar([1, 2, 3, 4], mr.mean(0), yerr=mr.std(0), fmt=mk + "-", color=c, capsize=3, ms=4, label=name)
a1.set_xlabel("operators M (K = 24 USVs)"); a1.set_ylabel("unsafe rate among hazards (%)"); a1.legend(frameon=False, fontsize=7.5)
a2.set_xlabel("operators M (K = 24 USVs)"); a2.set_ylabel("MRM events per hour")
a1.set_title("(a) safety", loc="left", fontsize=8.5); a2.set_title("(b) operational disruption", loc="left", fontsize=8.5)
for a in (a1, a2):
    a.set_xticks([1, 2, 3, 4]); a.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(f"{OUT}/fig6_operators.png", dpi=300); plt.close(fig)

# Fig 7 online trace
fig, ax = plt.subplots(figsize=(7.2, 2.6))
vv = [("static_L", "#d9822b"), ("online_L", "#2f6db3"), ("online_L_budget", "#1b3f73")] if "online_L" in Rs[0]["online"] else [("static", "#d9822b"), ("online", "#2f6db3")]
for v, c in vv:
    tr = np.array([R["online"][v]["roll"] for R in Rs]) * 100
    t = np.arange(tr.shape[1]) * 250 + 500
    ax.plot(t, tr.mean(0), color=c, label={"static_L": "static thresholds", "online_L": "online $\\lambda_{lo}$", "online_L_budget": "online $\\lambda_{lo}$ + budget", "static": "static thresholds", "online": "online thresholds"}[v])
    ax.fill_between(t, tr.mean(0) - tr.std(0), tr.mean(0) + tr.std(0), color=c, alpha=0.15)
ax.axvline(6000, color="#555", ls=":", lw=1); ax.text(6100, ax.get_ylim()[1] * 0.9, "shift onset", fontsize=7.5)
ax.axhline(2.0, color="#999", ls="--", lw=0.8); ax.text(200, 2.15, "$\\alpha$ = 2%", fontsize=7.5)
ax.set_xlabel("assessment index in stream"); ax.set_ylabel("rolling auto-clear miss (%)"); ax.legend(frameon=False)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(f"{OUT}/fig7_online.png", dpi=300); plt.close(fig)

# Fig 8 OOD unsafe bars
fig, ax = plt.subplots(figsize=(7.2, 2.8))
ms_ = ["Rule-CPA", "Selective-conf", "Ensemble-defer", "SCRC-global"] + (["LTT-help (RCIP-style)"] if "LTT-help (RCIP-style)" in Rs[0]["methods"] else []) + ["CORAL (ours)"] + (["CORAL-L (ours)"] if "CORAL-L (ours)" in Rs[0]["methods"] else [])
w = 0.8 / len(ms_)
for j, m in enumerate(ms_):
    vals = np.array([[R["ood"][m][s]["unsafe_rate"] for s in ["id"] * 0 + shifts] for R in Rs]) * 100
    idv = np.array([R["methods"][m]["unsafe_rate"] for R in Rs]) * 100
    allv = np.c_[idv, vals]
    ax.bar(np.arange(len(shifts) + 1) + (j - (len(ms_) - 1) / 2) * w, allv.mean(0), w, yerr=allv.std(0), color=C[m], label=m, capsize=1.5, error_kw=dict(lw=0.6))
NAMES = {"rough_sea": "rough sea", "ais_dropout": "AIS dropout", "dense_traffic": "dense traffic", "high_speed_craft": "high-speed", "link_degradation": "link degr."}
ax.set_xticks(range(len(shifts) + 1)); ax.set_xticklabels(["ID"] + [NAMES[x] for x in shifts])
ax.set_yscale("log"); ax.set_ylabel("unsafe rate among hazards (%)"); ax.legend(frameon=False, ncol=6, fontsize=6.5, loc="lower center", bbox_to_anchor=(0.5, 1.0))
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(f"{OUT}/fig8_ood.png", dpi=300); plt.close(fig)
print("figures done")
