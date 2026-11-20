# CORAL: risk-controlled takeover requests for satellite-supervised USVs

Code, data generators, trained-model predictions and results for the paper

> G. Arul Dalton, S. V. J. Mani. *Risk Controlled Takeover Requests for Satellite Supervised Unmanned Surface Vessels.*
> Submitted to the Journal of Marine Science and Technology (Springer).

A fleet of K unmanned surface vessels (USVs) is supervised by M operators in a remote operation centre (ROC) over
LEO, GEO or degraded satellite links. For every encounter assessment a vessel decides to **PROCEED**, request a
**TAKEOVER** by an operator, or **AVOID** autonomously. CORAL (conformal operator-risk allocation under link
constraints) provides

- a per-link-regime conformal bound on the share of hazards that are auto-cleared (Theorem 1),
- takeover budgets derived from ROC queueing capacity and link-dependent service time (workload-equalised, Prop. 1),
- **CORAL-F**, per-request conformal feasibility certificates: a resolution-time bound computed from the live ROC
  queue and a Mondrian bound on the true deadline. Infeasible requests become immediate AVOID; feasible requests get
  a certified timeout. The unsafe rate is then bounded by about alpha + gamma with no assumption on the queue,
  operators or link (Theorem 2),
- CORAL-L, the earlier lateness-proxy variant (Corollary 1), kept as a baseline,
- online updates of the thresholds and certificate quantiles under distribution shift (Prop. 2).

Everything is plain NumPy (analytic gradients, no deep-learning framework) and runs on a laptop CPU.

Full implementation details, equation-to-code mapping and every setting are in
[`docs/IMPLEMENTATION.md`](docs/IMPLEMENTATION.md).

## Quick start

```bash
git clone https://github.com/<user>/coral-usv-takeover.git
cd coral-usv-takeover
python -m venv .venv && source .venv/bin/activate      # optional
pip install -r requirements.txt
python -m unittest discover -s tests -v                  # smoke tests, about 1 min
python run_feasibility.py --res results --seed 0         # CORAL-F on saved predictions, a few seconds
```

`run_feasibility.py` works directly on the saved ensemble predictions in `results/` and `results_ais/`, so the
CORAL-F tables (Tables 16 and 17 of the paper) can be checked without retraining.

## Reproduce the paper

```bash
bash reproduce.sh            # sandbox: train + evaluate 5 seeds, all tables and figures (about 30 min)
bash reproduce.sh --ais      # also the real-traffic AIS replay (needs data/ct_dma, see data/README.md)
```

or step by step:

```bash
python -c "from coral.model import grad_check; print(grad_check())"     # about 1e-7
for s in 0 1 2 3 4; do python run_experiments.py --seed $s --out results; done
python aggregate.py results            # Tables 3-12 -> results/summary_tables.md, result figures
python analysis_v3.py results          # Tables 13 and 15, assumption checks (Sect. 8.7)
python frontier.py results results_ais # Table 14, Fig. 11 (matched-cost frontiers)
for s in 0 1 2 3 4; do python run_feasibility.py --res results --seed $s; done
python aggregate_feas.py results       # Tables 16-17 -> results/feas_tables.md
python fig_feas.py                     # Figs. 12-13
python figures_system.py               # Figs. 1-3 (system-model diagrams)
```

Real traffic (AIS replay): `for s in 0 1 2 3 4; do python run_experiments.py --seed $s --source ais --out results_ais; done`,
then the same analysis scripts with `results_ais`, plus `python fig_ais.py` and `python fig_ais_map.py` (Figs. 4, 10).

## Repository layout

| Path | Content | Paper |
|---|---|---|
| `coral/sim.py` | Sandbox: encounters, radar and AIS sensing, LEO/GEO/degraded links | Sect. 4.1-4.3, 6.1; Eqs. (1)-(7) |
| `coral/ais_replay.py` | AIS replay testbed on real Danish Maritime Authority trajectories | Sect. 6.5, 8.5 |
| `coral/safe_pickle.py` | Restricted unpickler (NumPy arrays only) for the AIS pickles | |
| `coral/model.py` | LCSA set-attention network, deep ensemble, temperature scaling, gradient check | Sect. 5.1-5.3; Eqs. (11)-(17) |
| `coral/conformal.py` | Conformal thresholds, three-way rule, workload budgets, CORAL-L, online updates, LTT baseline | Sect. 5.4-5.9; Eqs. (18)-(31) |
| `coral/fleet.py` | ROC queue simulator (M operators, urgency queue, MRM timeouts) and fleet metrics | Sect. 4.3-4.4; Eqs. (8)-(10), (24) |
| `coral/feasibility.py` | CORAL-F: certificates, certified timeout, rerouting, policy-consistent calibration, online quantiles | Sect. 5.10; Eqs. (32)-(38) |
| `run_experiments.py` | One seed end to end: data, training, all baselines, ablations, shifts, sweeps, online stream | Sect. 6-8 |
| `run_feasibility.py` | CORAL-F experiments on saved predictions: variants, ablations, frontier, audit, shift stream | Sect. 8.8 |
| `aggregate.py`, `aggregate_feas.py` | Seed aggregation into Markdown tables and JSON summaries | Tables 3-12, 16-17 |
| `analysis_v3.py`, `frontier.py` | Paired bootstrap, assumption checks, calibration-size sweep, matched-cost frontiers | Tables 13-15 |
| `fig_*.py`, `figures_system.py` | All figures | Figs. 1-13 |
| `results/`, `results_ais/` | Per-seed JSON results, saved predictions (`seed*_preds.npz`), bootstrap arrays, tables | |
| `figures/`, `figures_ais/` | Rendered figures | |
| `tests/` | Smoke tests (gradient check, conformal quantile, queue simulator, Theorem 2 sanity check) | |
| `docs/IMPLEMENTATION.md` | Implementation details | |
| `data/README.md` | How to obtain the AIS data | |

## Main results (5 seeds, K = 24 USVs, M = 2 operators)

| Unsafe rate among hazards | CORAL-F | CORAL-L | CORAL | SCRC-global |
|---|---|---|---|---|
| Sandbox, in distribution | 1.95 ± 0.20% | 1.98 ± 0.18% | 2.15 ± 0.29% | 2.50 ± 0.26% |
| Sandbox, AIS dropout | **1.85 ± 0.21%** | 2.92 ± 1.66% | 8.41 ± 2.20% | 8.86 ± 1.36% |
| Real AIS traffic, in distribution | 2.05 ± 0.25% | 2.08 ± 0.29% | 2.09 ± 0.29% | 2.98 ± 0.77% |
| Real AIS traffic, AIS dropout | **2.07 ± 0.43%** | 11.53 ± 3.76% | 13.16 ± 2.98% | 11.28 ± 3.15% |

In distribution the certificate costs 0.15-0.36 points of safety at matched manoeuvre cost; under AIS dropout it is
the only method that stays near the 2% target. See `results/feas_tables.md` and `results_ais/feas_tables.md`.

## Requirements

Python >= 3.10 (tested with 3.13), NumPy, SciPy, scikit-learn, Matplotlib (tested versions in `requirements.txt`).
One sandbox seed takes about 5 min on two CPU cores; one AIS seed about 15 min.

## Limitations

Radar, AIS reception, satellite links and operators are simulated; in the AIS replay the trajectories are real but
replayed vessels do not react to the USV and hazards are enriched to 25%. No field trials were run. See Sect. 9 of
the paper.

## Citation

See `CITATION.cff`. A BibTeX entry will be added after publication.

## Licence

MIT (see `LICENSE`). The AIS data are not part of this repository and remain under their original terms.
