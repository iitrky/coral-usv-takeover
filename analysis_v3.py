"""New methodology analyses: paired bootstrap CIs, proxy validity, calibration size, online bounds, LTT."""
import glob, json, sys, numpy as np
RD = sys.argv[1]
Rs = [json.load(open(f)) for f in sorted(glob.glob(f"{RD}/seed[0-9].json"))]
B = [np.load(f) for f in sorted(glob.glob(f"{RD}/seed[0-9]_boot.npz"))]
out = []
ALPHA = 0.02
# paired, seed-stratified bootstrap over hazards
rng = np.random.default_rng(0)
pairs = [("CORAL-L", "SCRC-global"), ("CORAL-L", "LTT-help"), ("CORAL", "SCRC-global"), ("CORAL-L", "CORAL")]
out.append("## Paired bootstrap of unsafe-rate difference (pp), 10,000 resamples, stratified by seed")
out.append("| A - B | mean diff | 95% CI | P(diff >= 0) |\n|---|---|---|---|")
for a, b in pairs:
    da = [x[a] for x in B]; db = [x[b] for x in B]
    point = np.mean(np.concatenate(da)) - np.mean(np.concatenate(db))
    diffs = []
    for _ in range(10000):
        sa, sb = [], []
        for xa, xb in zip(da, db):
            i = rng.integers(0, len(xa), len(xa))
            sa.append(xa[i]); sb.append(xb[i])
        diffs.append(np.mean(np.concatenate(sa)) - np.mean(np.concatenate(sb)))
    diffs = np.array(diffs) * 100
    out.append(f"| {a} - {b} | {point*100:.2f} | [{np.percentile(diffs,2.5):.2f}, {np.percentile(diffs,97.5):.2f}] | {np.mean(diffs >= 0):.4f} |")
out.append(f"\nhazards per seed: {[len(x['CORAL']) for x in B]}")
# proxy validity
out.append("\n## Lateness proxy validity (pooled over seeds; CORAL budget thresholds)")
for sp in Rs[0]["proxy"]:
    a = sum(R["proxy"][sp]["n_actual_late"] for R in Rs); c = sum(R["proxy"][sp]["caught"] for R in Rs); p = sum(R["proxy"][sp]["n_proxy"] for R in Rs)
    out.append(f"{sp}: actually late {a}, flagged by proxy {p}, actually-late flagged {c} -> recall {c/max(a,1):.3f}, precision {c/max(p,1):.3f}")
# calibration size
out.append("\n## Calibration size (D1 samples): test auto-clear miss %, share of draws above alpha, SD of lam_lo per regime")
out.append("| n1 | miss mean | miss SD | P(miss > alpha) | SD lam LEO | SD lam GEO | SD lam DEG | miss LEO | miss GEO | miss DEG |\n|---|---|---|---|---|---|---|---|---|---|")
for n in ["250", "500", "1000", "2000", "4000", "6000"]:
    C = [R["calsize"][n] for R in Rs]
    sd = np.mean([c["lam_sd"] for c in C], 0); pg = np.mean([c["per_group_mean"] for c in C], 0) * 100
    out.append(f"| {n} | {np.mean([c['miss_mean'] for c in C])*100:.2f} | {np.mean([c['miss_sd'] for c in C])*100:.2f} | {np.mean([c['frac_above'] for c in C]):.2f} | {sd[0]:.3f} | {sd[1]:.3f} | {sd[2]:.3f} | {pg[0]:.2f} | {pg[1]:.2f} | {pg[2]:.2f} |")
# online bounds
out.append("\n## Online update bounds (online_L_budget stream)")
out.append("| regime | hazards T | |avg upd err - alpha| | bound | takeover - beta | bound |\n|---|---|---|---|---|---|")
for g in ["0", "1", "2"]:
    Bd = [R["online"]["online_L_budget"]["bounds"][g] for R in Rs]
    dev = [abs(b["upd_err"] - ALPHA) for b in Bd if b["upd_err"] is not None]
    out.append(f"| {g} | {np.mean([b['T_haz'] for b in Bd]):.0f} | {np.mean(dev)*100:.2f} (max {np.max(dev)*100:.2f}) | {np.mean([b['bound_lo'] for b in Bd])*100:.2f} | "
               f"{np.mean([b['takeover']-b['beta'] for b in Bd])*100:.2f} (max {np.max([b['takeover']-b['beta'] for b in Bd])*100:.2f}) | {np.mean([b['bound_hi'] for b in Bd])*100:.2f} |")
out.append("\nLTT thresholds: " + str([(round(R['ltt']['lo'],3), round(R['ltt']['hi'],3)) for R in Rs]) + f" grid N={Rs[0]['ltt']['N']}")
open(f"{RD}/analysis_v3.md", "w").write("\n".join(out))
print("\n".join(out))
