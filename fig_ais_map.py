import os
"""Fig. 9: AIS replay region with real test-period tracks and coastline."""
import numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from coral.safe_pickle import load
DIR = os.environ.get("CORAL_AIS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ct_dma"))
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8.5})
coast = load(f"{DIR}/dma_coastline_polygons.pkl")
D = load(f"{DIR}/ct_dma_test.pkl")
fig, ax = plt.subplots(figsize=(5.2, 4.6))
for d in D:
    tr = d["traj"]
    ax.plot(10.3 + tr[:, 1] * 2.7, 55.5 + tr[:, 0] * 2.5, lw=0.25, color="#2f6db3", alpha=0.35)
polys = coast if isinstance(coast, (list, tuple)) else [coast]
for p in polys:
    p = np.asarray(p)
    if p.ndim == 2 and p.shape[1] >= 2:
        lon, lat = (p[:, 1], p[:, 0]) if p[:, 0].max() < 60 and p[:, 0].min() > 50 else (p[:, 0], p[:, 1])
        ax.fill(lon, lat, color="#d8d3c4", ec="#8a8270", lw=0.4)
ax.set_xlim(10.3, 13.0); ax.set_ylim(55.5, 58.0)
ax.set_xlabel("longitude (°E)"); ax.set_ylabel("latitude (°N)")
ax.set_aspect(1 / np.cos(np.deg2rad(56.75)))
ax.text(10.35, 57.92, f"{len(D):,} test tracks, 21–31 March 2019", fontsize=7.5, va="top", bbox=dict(fc="white", ec="none", alpha=0.85, pad=1.5))
fig.tight_layout(); fig.savefig("figures_ais/fig9_ais_map.png", dpi=300)
print(type(coast), len(polys), np.asarray(polys[0]).shape)
