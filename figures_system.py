"""System-model diagrams (Figs. 1-3) drawn with matplotlib."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle, Polygon

OUT = "figures"
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})
INK, BLUE, ORANGE, GREEN, RED, GREY = "#1f2a36", "#2f6db3", "#d9822b", "#3a8f5c", "#b8433b", "#8a96a3"


def box(ax, x, y, w, h, text, fc="#ffffff", ec=INK, fs=8.5, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.02",
                                fc=fc, ec=ec, lw=1.0))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal", color=INK, wrap=True)


def arrow(ax, p, q, color=INK, style="-|>", lw=1.0, ls="-", rad=0.0):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=9, color=color, lw=lw,
                                 linestyle=ls, connectionstyle=f"arc3,rad={rad}"))


def ship(ax, x, y, s=0.035, c=BLUE):
    ax.add_patch(Polygon([[x - s, y], [x + s, y], [x + 1.4 * s, y + 0.5 * s], [x - s, y + 0.5 * s]],
                         closed=True, fc=c, ec=INK, lw=0.6))
    ax.add_patch(Polygon([[x - 0.3 * s, y + 0.5 * s], [x + 0.4 * s, y + 0.5 * s], [x + 0.4 * s, y + 0.95 * s],
                          [x - 0.3 * s, y + 0.95 * s]], closed=True, fc="#dfe6ee", ec=INK, lw=0.5))


# ---------------- Fig 1: architecture ----------------
fig, ax = plt.subplots(figsize=(7.2, 4.0))
ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
ax.add_patch(plt.Rectangle((0, 0), 1, 0.30, fc="#e8f1f8", ec="none"))
ax.text(0.01, 0.02, "Sea surface: K satellite-supervised USVs and non-cooperative target ships", fontsize=7.5, color=GREY)
for i, x in enumerate([0.08, 0.22, 0.36, 0.50]):
    ship(ax, x, 0.16)
    ax.text(x, 0.10, f"USV$_{{{i+1 if i < 3 else 'K'}}}$", ha="center", fontsize=8)
ax.text(0.43, 0.18, "...", fontsize=12)
for x, y in [(0.15, 0.24), (0.30, 0.06), (0.58, 0.22)]:
    ship(ax, x, y, s=0.02, c=GREY)
ax.add_patch(Circle((0.22, 0.17), 0.09, fill=False, ec=ORANGE, ls="--", lw=0.8))
ax.text(0.22, 0.275, "radar / AIS\nencounter tokens", ha="center", fontsize=7, color=ORANGE)
# satellites
for x, lab, c in [(0.18, "LEO\nRTT 40-120 ms\n20-80 Mbit/s", GREEN), (0.50, "GEO\nRTT 550-800 ms\n1-4 Mbit/s", BLUE)]:
    ax.add_patch(plt.Rectangle((x - 0.025, 0.80), 0.05, 0.035, fc=c, ec=INK, lw=0.6))
    ax.plot([x - 0.06, x + 0.06], [0.817, 0.817], color=INK, lw=2)
    ax.text(x, 0.93, lab.replace("\n", "  "), fontsize=7, ha="center", va="center")
for xs in [0.08, 0.22, 0.36]:
    arrow(ax, (xs, 0.21), (0.18, 0.78), color=GREEN, style="<|-|>", lw=0.7)
arrow(ax, (0.50, 0.21), (0.52, 0.78), color=BLUE, style="<|-|>", lw=0.7)
arrow(ax, (0.36, 0.21), (0.52, 0.78), color=RED, style="<|-|>", lw=0.7, ls=(0, (3, 2)))
ax.text(0.27, 0.50, "degraded regime\n(outage, rain fade)\nRTT 1.5-6 s, <0.5 Mbit/s", fontsize=6.8, color=RED)
# ROC
box(ax, 0.72, 0.34, 0.26, 0.44, "", fc="#f6f6f2")
ax.text(0.85, 0.75, "Remote Operation Centre", ha="center", fontsize=7.8, fontweight="bold")
box(ax, 0.745, 0.60, 0.21, 0.09, "urgency-ordered\ntakeover queue Q(t)", fc="#fff4e6", fs=7.5)
box(ax, 0.745, 0.47, 0.095, 0.09, "operator 1", fs=7.5)
box(ax, 0.86, 0.47, 0.095, 0.09, "operator M", fs=7.5)
ax.text(0.85, 0.40, "service time  $\\tau_i=\\tau_h+8S/B_i+2\\,RTT_i$", ha="center", fontsize=7)
arrow(ax, (0.21, 0.80), (0.72, 0.72), color=GREEN, style="<|-|>", lw=0.8, rad=-0.25)
arrow(ax, (0.55, 0.81), (0.72, 0.66), color=BLUE, style="<|-|>", lw=0.8)
arrow(ax, (0.85, 0.60), (0.80, 0.56)); arrow(ax, (0.85, 0.60), (0.905, 0.56))
ax.text(0.85, 0.22, "PROCEED / AVOID decided onboard;\nTAKEOVER requests consume operator time;\ntimeout $\\Rightarrow$ minimum-risk manoeuvre (MRM)",
        ha="center", fontsize=7, color=INK)
fig.savefig(f"{OUT}/fig1_architecture.png", dpi=300, bbox_inches="tight"); plt.close(fig)

# ---------------- Fig 2: onboard pipeline ----------------
fig, ax = plt.subplots(figsize=(7.4, 3.3))
ax.set_xlim(-0.01, 1.03); ax.set_ylim(0, 1); ax.axis("off")
box(ax, 0.00, 0.62, 0.13, 0.22, "Radar scans\n(3 per target)\nAIS reports\n(age, dropouts)", fs=7.2)
box(ax, 0.00, 0.30, 0.13, 0.22, "Context\nsea state, own\nspeed, RTT,\nbandwidth", fs=7.2)
box(ax, 0.17, 0.55, 0.14, 0.32, "Token builder\n(Sec. 4.1)\nfused pos/vel,\nDCPA, TCPA,\nvalidity masks,\nAIS age", fs=7.2, fc="#eef4fb")
box(ax, 0.35, 0.30, 0.17, 0.57, "LCSA ensemble\n(Sec. 4.2)\n\nper-target MLP\ncontext query q\nmasked attention\n+ worst-target pool\n\n5 members,\ntemperature T", fs=7.2, fc="#eef4fb")
box(ax, 0.56, 0.52, 0.14, 0.30, "Score\n$r=\\bar p+\\kappa\\,\\sigma$\n(Eq. 16)", fs=7.5, fc="#fff4e6")
box(ax, 0.56, 0.12, 0.14, 0.30, "Link regime\n$g\\in${LEO,GEO,\nDEG}\nbudget $\\beta_g$\n(Eq. 22)", fs=7.2, fc="#fff4e6")
box(ax, 0.74, 0.36, 0.11, 0.36, "Three-way\nrule\n$\\lambda_{lo}(g)$\n$\\lambda_{hi}(g)$\n(Eqs. 18-21)", fs=7.2, fc="#fff4e6")
box(ax, 0.885, 0.70, 0.115, 0.13, "PROCEED", fs=7.5, fc="#e6f2ea")
box(ax, 0.885, 0.47, 0.115, 0.13, "TAKEOVER\n$\\rightarrow$ ROC queue", fs=7, fc="#fdf0dc")
box(ax, 0.885, 0.24, 0.115, 0.13, "AVOID\n(COLREG man.)", fs=7, fc="#f8e3e1")
for a, b in [((0.13, 0.73), (0.17, 0.71)), ((0.31, 0.71), (0.35, 0.71)), ((0.13, 0.41), (0.35, 0.41)),
             ((0.52, 0.67), (0.56, 0.67)), ((0.70, 0.67), (0.74, 0.60)), ((0.70, 0.27), (0.74, 0.45)),
             ((0.85, 0.62), (0.885, 0.76)), ((0.85, 0.54), (0.885, 0.53)), ((0.85, 0.46), (0.885, 0.30))]:
    arrow(ax, a, b)
arrow(ax, (0.52, 0.41), (0.56, 0.32))
ax.text(0.435, 0.22, "$\\sigma$: ensemble spread", ha="center", fontsize=6.8, color=GREY)
arrow(ax, (0.94, 0.24), (0.80, 0.08), color=GREY, ls=(0, (3, 2)), rad=-0.3)
ax.text(0.80, 0.02, "delayed labels $\\rightarrow$ online CRC update of $\\lambda_{lo}(g)$ (Eq. 25)", ha="center", fontsize=7, color=GREY)
fig.savefig(f"{OUT}/fig2_pipeline.png", dpi=300, bbox_inches="tight"); plt.close(fig)

# ---------------- Fig 3: decision bands + timing ----------------
fig, (a1, a2) = plt.subplots(2, 1, figsize=(7.2, 3.6), gridspec_kw=dict(height_ratios=[1.1, 1]))
regs = [("LEO", 0.06, 0.30), ("GEO", 0.06, 0.18), ("DEG", 0.05, 0.08)]
for k, (lab, lo, hi) in enumerate(regs):
    yk = 2 - k
    a1.barh(yk, lo, color="#cfe7d7", ec=INK, lw=0.5)
    a1.barh(yk, hi - lo, left=lo, color="#fbe0b8", ec=INK, lw=0.5)
    a1.barh(yk, 1 - hi, left=hi, color="#f3c9c4", ec=INK, lw=0.5)
    a1.text(-0.01, yk, lab, ha="right", va="center", fontsize=8)
a1.text(0.03, 2.45, "PROCEED", fontsize=7); a1.text(0.15, 2.45, "TAKEOVER", fontsize=7); a1.text(0.55, 2.45, "AVOID", fontsize=7)
a1.set_xlim(0, 1); a1.set_yticks([]); a1.set_xlabel("risk score $r=\\bar p+\\kappa\\sigma$ (illustrative thresholds)", fontsize=8)
a1.set_title("(a) link-stratified three-way decision bands: band width shrinks as service time $\\tau_g$ grows", fontsize=8.5, loc="left")
for s in ["top", "right", "left"]:
    a1.spines[s].set_visible(False)
a2.set_xlim(0, 100); a2.set_ylim(0, 1); a2.axis("off")
a2.annotate("", (95, 0.5), (2, 0.5), arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.8))
pts = [(4, "$t_i$ request"), (22, "start of\nservice"), (40, "uplink\n$8S/B_i$"), (48, "2 RTT"), (70, "human\n$\\tau_h$"), (84, "$T_i^{out}$\nMRM"), (92, "$t^\\star_i-T_{man}$\ndeadline")]
for x, lab in pts:
    a2.plot([x, x], [0.42, 0.58], color=INK, lw=0.8)
    a2.text(x, 0.66, lab, ha="center", fontsize=7)
a2.add_patch(plt.Rectangle((4, 0.44), 18, 0.12, fc="#dfe6ee", ec="none")); a2.text(13, 0.25, "queue wait $W_i$", ha="center", fontsize=7)
a2.add_patch(plt.Rectangle((22, 0.44), 48, 0.12, fc="#fbe0b8", ec="none")); a2.text(46, 0.25, "service $\\tau_i$", ha="center", fontsize=7)
a2.set_title("(b) takeover timeline: unsafe if neither operator nor MRM acts before $t^\\star_i-T_{man}$ (Eq. 9)", fontsize=8.5, loc="left")
fig.tight_layout()
fig.savefig(f"{OUT}/fig3_decision_timing.png", dpi=300, bbox_inches="tight"); plt.close(fig)
print("ok")
