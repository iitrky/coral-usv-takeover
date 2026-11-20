"""Aggregate CORAL-F results over seeds: mean ± std tables, paired bootstrap, frontier, audit."""
import json, sys, os
import numpy as np

KEYS = [("unsafe_rate", "Unsafe %"), ("late_takeover_hazard", "Late %"), ("false_manoeuvre", "FM %"),
        ("total_manoeuvre", "Total man. %"), ("takeover_rate", "Takeover %")]


def ms(v):
    v = np.array(v) * 100
    return f"{v.mean():.2f} ± {v.std(ddof=1):.2f}"


def main(res):
    Rs = [json.load(open(os.path.join(res, f"seed{s}_feas.json"))) for s in range(5)]
    out = {}
    lines = [f"## {res}", "", "### In-distribution test", "| Method | " + " | ".join(k[1] for k in KEYS) + " |",
             "|" + "---|" * (len(KEYS) + 1)]
    for nm in Rs[0]["methods"]:
        row = [ms([R["methods"][nm][k] for R in Rs]) for k, _ in KEYS]
        out.setdefault("methods", {})[nm] = {k: float(np.mean([R["methods"][nm][k] for R in Rs])) for k, _ in KEYS}
        lines.append(f"| {nm} | " + " | ".join(row) + " |")
    for s in Rs[0]["shift"]["CORAL"]:
        lines += ["", f"### Shift: {s}", "| Method | " + " | ".join(k[1] for k in KEYS) + " |", "|" + "---|" * (len(KEYS) + 1)]
        for nm in Rs[0]["shift"]:
            row = [ms([R["shift"][nm][s][k] for R in Rs]) for k, _ in KEYS]
            out.setdefault("shift", {}).setdefault(s, {})[nm] = {k: float(np.mean([R["shift"][nm][s][k] for R in Rs])) for k, _ in KEYS}
            lines.append(f"| {nm} | " + " | ".join(row) + " |")
    # certificate coverage
    lines += ["", "### Certificate coverage (CORAL-F, ID test)"]
    cR = [R["methods"]["CORAL-F"]["cov_R"] for R in Rs]; cD = [R["methods"]["CORAL-F"]["cov_D"] for R in Rs]
    dl = [R["cert"]["delta"] for R in Rs]
    lines.append(f"cov_R {np.mean(cR):.3f}±{np.std(cR, ddof=1):.3f}, cov_D {np.mean(cD):.3f}±{np.std(cD, ddof=1):.3f}, target 1-delta = {1-np.mean(dl):.3f}")
    for s in Rs[0]["shift"]["CORAL-F"]:
        cD = [R["shift"]["CORAL-F"][s]["cov_D"] for R in Rs]; cR = [R["shift"]["CORAL-F"][s]["cov_R"] for R in Rs]
        lines.append(f"  {s}: cov_R {np.mean(cR):.3f}, cov_D {np.mean(cD):.3f}")
    out["cert"] = dict(delta=float(np.mean(dl)), qR=float(np.mean([R["cert"]["qR"] for R in Rs])),
                       qD=np.mean([R["cert"]["qD"] for R in Rs], axis=0).tolist(),
                       pi_T=float(np.mean([R["cert"]["pi_T"] for R in Rs])))
    # audit recall
    lines += ["", "### Lateness recall of the certificate (audit, no routing), pooled over seeds"]
    for s in Rs[0]["audit"]:
        nl = sum(R["audit"][s]["static"]["n_late"] for R in Rs); cg = sum(R["audit"][s]["static"]["caught"] for R in Rs)
        lines.append(f"  {s}: {cg}/{nl} = {100*cg/max(1,nl):.1f}%")
        out.setdefault("audit", {})[s] = dict(n_late=nl, caught=cg)
    # bootstrap CORAL-F minus others, pooled over seeds, paired per hazard
    lines += ["", "### Paired bootstrap (ID test), CORAL-F − X, unsafe pp"]
    B = [np.load(os.path.join(res, f"seed{s}_fboot.npz")) for s in range(5)]
    rng = np.random.default_rng(0)
    for other in ("SCRC-global", "CORAL", "CORAL-L"):
        diffs = []; wins = 0
        for b in B:
            dlt = b["CORAL-F"].astype(float) - b[other].astype(float)
            wins += dlt.mean() < 0
            diffs.append(dlt)
        dd = np.concatenate(diffs)
        bs = [dd[rng.integers(0, len(dd), len(dd))].mean() for _ in range(2000)]
        lo, hi = np.percentile(bs, [2.5, 97.5])
        lines.append(f"  vs {other}: {100*dd.mean():.2f} [{100*lo:.2f}, {100*hi:.2f}], lower in {wins}/5 seeds")
        out.setdefault("boot", {})[other] = [100 * dd.mean(), 100 * lo, 100 * hi, int(wins)]
    # frontier
    lines += ["", "### Frontier (mean over seeds): alpha -> unsafe %, total manoeuvre %"]
    for s in Rs[0]["frontier"]:
        for nm in Rs[0]["frontier"][s]:
            pts = []
            for i in range(len(Rs[0]["frontier"][s][nm])):
                u = np.mean([R["frontier"][s][nm][i]["unsafe"] for R in Rs]) * 100
                t = np.mean([R["frontier"][s][nm][i]["totM"] for R in Rs]) * 100
                pts.append((Rs[0]["frontier"][s][nm][i]["alpha"], round(u, 2), round(t, 1)))
            out.setdefault("frontier", {}).setdefault(s, {})[nm] = pts
            lines.append(f"  {s} {nm}: {pts}")
    if "stream" in Rs[0]:
        lines += ["", "### Stream ID -> AIS dropout"]
        for m in ("static", "online"):
            lines.append(f"  {m}: unsafe_post {ms([R['stream'][m]['unsafe_post'] for R in Rs])}, "
                         f"late_post {ms([R['stream'][m]['late_post'] for R in Rs])}, fm_post {ms([R['stream'][m]['fm_post'] for R in Rs])}")
    open(os.path.join(res, "feas_tables.md"), "w").write("\n".join(lines))
    json.dump(out, open(os.path.join(res, "feas_summary.json"), "w"), indent=1)
    print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1])
