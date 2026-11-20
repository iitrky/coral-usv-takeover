# Implementation details

This document describes every component of the CORAL implementation, the settings used in the paper, and how
each table and figure is produced. Section, equation, table and figure numbers refer to the paper.

## 1. Pipeline overview

```
 sim.py / ais_replay.py         model.py                conformal.py              fleet.py / feasibility.py
 encounters + sensing  ──►  tokens ──► LCSA ensemble ──► score r = p̄ + κσ ──► PROCEED / TAKEOVER / AVOID ──► ROC queue
 + link regime + labels        (Eqs. 11-17)              thresholds per link      (Eq. 19)                 (M operators,
                                                          (Eqs. 18, 20, 22)                                 MRM timeouts,
                                                          CORAL-L (Eqs. 26-27)                              CORAL-F certificates
                                                                                                            Eqs. 32-38)
```

One call of `run_experiments.py --seed s` generates all data for seed s, trains three five-member ensembles
(LCSA, LCSA without context query, set-MLP), calibrates every method on the calibration splits, and evaluates
all methods, ablations, shifts and sweeps in the queue simulator. It saves:

| File | Content |
|---|---|
| `results/seed{s}.json` | All fleet metrics per method, shift, sweep and ablation; predictor metrics; budgets; LTT thresholds |
| `results/seed{s}_preds.npz` | Ensemble mean and spread of the LCSA ensemble on D1, D2, test and every shifted set, with labels, link regime, true and estimated time to closest approach, bandwidth and RTT |
| `results/seed{s}_boot.npz` | Per-hazard unsafe indicators on the test set for the paired bootstrap |
| `results/seed0_arrays.npz` | Arrays for the calibration figures (seed 0 only) |

`run_feasibility.py` reuses `seed{s}_preds.npz`, re-derives the CORAL, CORAL-L and SCRC-global thresholds exactly
as `run_experiments.py` does, and evaluates CORAL-F. It writes `seed{s}_feas.json`, `seed{s}_fboot.npz` and, for
seed 0, `seed0_fstream.npz` (online quantile traces).

Random streams: data use `default_rng(seed)`; the queue simulator uses `default_rng(7 s + 1)` on the test set,
`7 s + 2` on shifted sets, `7 s + 5` on D2 for calibration simulations. All results are therefore deterministic.

## 2. Testbeds

### 2.1 Sandbox (`coral/sim.py`)

`generate(n, rng, **overrides)` returns a dict of arrays: `X` (n × 8 × 16 tokens), `M` (n × 8 mask), `C` (n × 6
context), `y` (hazard label), `tcpa_true` (time of first violation t*), `est_tcpa` (onboard estimate t̂), `link`
(0 LEO, 1 GEO, 2 degraded), `rtt`, `bw`, `sea`.

| Setting (`DEFAULT_CFG`) | Value |
|---|---|
| Own speed | U[3, 8] m/s |
| Targets per assessment | 1-6, speed U[2, 12] m/s |
| Collision-course probability | 0.18 (aimed at own ship at U[40, 420] s, Gaussian offset 350 m) |
| Unannounced target turn | probability 0.3, 20-90° (Eq. 2) |
| Sea state s | U[0, 0.6] in distribution |
| Radar | range noise 8 + 25 s m, bearing noise 0.4 + 1.5 s deg (Eq. 5); detection probability Eq. (6); scans at -20, -10, 0 s |
| AIS | dropout 0.10, base age U[0, 30] s, 10 m position and 0.2 m/s velocity noise (Eq. 7); relayed age includes link delay |
| Links | LEO 0.65 (RTT 0.04-0.12 s, 20-80 Mbit/s), GEO 0.25 (0.55-0.80 s, 1-4 Mbit/s), degraded 0.10 (1.5-6 s, 0.1-0.5 Mbit/s); bandwidth log-uniform |
| Horizon, safety domain | H = 300 s, d_s = 300 m, ground truth at 5 s steps (Eqs. 3-4) |

Shifted test sets (`OOD_SPECS` in `run_experiments.py`): rough sea (s ∈ [0.7, 1.0]), AIS dropout (0.6), dense
traffic (5-8 targets), high-speed craft (12-22 m/s), link degradation (regime mix 0.3/0.3/0.4).

Split sizes per seed: 40,000 train, 5,000 validation (temperature), 6,000 D1, 6,000 D2, 20,000 test, 8,000 per
shifted set.

### 2.2 AIS replay (`coral/ais_replay.py`)

`load_tracks(path)` reads the TrAISformer `ct_dma_{train,valid,test}.pkl` files through `safe_pickle.load`, which
only reconstructs NumPy arrays. `generate_ais(pool, n, rng, H=1200, d_s=500, hazard_frac=0.25)` picks an own ship
underway at a random time, takes all vessels within 7 km whose tracks cover the horizon as targets (8 nearest kept),
interpolates positions linearly, rotates to the own-ship frame, labels with the *actual* future tracks
(dt = 10 s), and samples stratified by label so that 25% of assessments are hazards (natural rate about 3%).
Radar, AIS dropout/age, sea state, links and the ROC are simulated exactly as in the sandbox.
Splits: train file → training (30,000) and temperature (4,000); validation file → D1, D2 (6,000 each);
test file → test (15,000) and three shifted sets (6,000 each). Calibration and test are separated in time.

## 3. Input representation (`coral/sim.py`, Eq. 11)

Each detected target becomes a 16-dimensional token: scaled relative position and velocity, radar-only velocity,
log range, estimated d_cpa and t_cpa (Eq. 11), approaching flag, fraction of scans that detected the target, latest-scan
flag, radar-velocity validity flag, AIS flag, AIS age, AIS speed. Fusion: latest radar fix, else AIS position
dead-reckoned by its age, else the last radar fix propagated. Velocity from AIS when available, else the finite
difference of radar fixes. Context vector (6): sea state, own speed, number of visible targets, log RTT,
log bandwidth, regime index.

## 4. LCSA network and ensemble (`coral/model.py`)

`LCSA(F=16, Cdim=6, d=48, attention=True, use_context=True)`:

| Step | Equation | Code |
|---|---|---|
| Token embedding h_j = ReLU(W1 x_j + b1) m_j | (12) | `forward` |
| Context query q = tanh(Wq c + bq) | (13) | `forward` |
| Scaled dot-product attention with mask | (14) | `forward` |
| Read-out z = [Σ a_j h_j ; max_j h_j ; q], two-layer head, logit ℓ | (15) | `forward` |
| Binary cross-entropy + weight decay | (17) | `fit`, `backward` (analytic gradients) |

Training: Adam, learning rate 2e-3 with cosine decay, 15 epochs, batch 256, weight decay 1e-5, each member on a
bootstrap resample with its own seed. `fit_temperature` fits one temperature per member on the validation split.
`Ensemble(m=5).predict` returns the ensemble mean p̄ and spread σ (Eq. 16). `grad_check()` compares analytic and
finite-difference gradients (max relative error about 1e-7). Ablation networks: `attention=False` (set-MLP with
mean and max pooling) and `use_context=False`.

## 5. Conformal decision layer (`coral/conformal.py`)

| Function | Paper | Notes |
|---|---|---|
| `score(p_mean, p_std, kappa)` | Eq. (16) | r = p̄ + κσ, κ = 1 |
| `crc_largest_lambda` | Eqs. (18), (20), (27) | largest λ on a 2,001-point grid with corrected risk ≤ target |
| `calibrate_lo(r, y, groups, alpha, grid, stratified)` | Eq. (18) | per-regime miss bound on D1 hazards, α = 0.02 |
| `calibrate_hi(r, groups, lam_lo, beta, grid)` | Eq. (20) | per-regime takeover budget on D2 |
| `decide(r, groups, lam_lo, lam_hi)` | Eq. (19) | three-way rule |
| `service_time(bw, rtt, tau_h, payload_MB)` | Eq. (8) | τ = τ_h + 8S/B + 2 RTT, S = 4 MB |
| `workload_budgets(...)` | Eq. (22) | β_g = min(β_cap, ρ_max M / (K r_e τ̄_g)), ρ_max = 0.7, β_cap = 0.35 |
| `late_proxy`, `calibrate_hi_lateness` | Eqs. (26)-(27) | CORAL-L, γ = 0.005 |
| `OnlineCRC` | Eq. (25) | η = 0.02, label delay D = 50 |
| `OnlineBudget` | Eq. (29) | η_b = 0.002 |
| `online_bound` | Eqs. (30)-(31) | deterministic long-run bounds |
| `ltt_thresholds(r, y, alpha, beta, delta=0.1)` | baseline | Learn-then-Test, 3,876 pairs, binomial tests, Bonferroni |

## 6. ROC queue simulator (`coral/fleet.py`)

`simulate(decisions, y, tcpa_true, est_tcpa, bw, rtt, rng, K=24, M_ops=2, r_e=1/60, T_man=30, priority)` is an
event-driven M-server queue. Assessments arrive as a Poisson stream of rate K r_e. TAKEOVER requests are queued;
with `priority="urgency"` a free operator takes the request with the earliest estimated deadline (Eq. 24), with
`"fcfs"` the oldest. Service time = 8S/B + 2 RTT + τ_h, τ_h log-normal (median 20 s, σ = 0.4). A request not
resolved within its timeout T_out = max(t̂ − T_man, 10 s) triggers a minimum-risk manoeuvre (MRM). A hazard is
unsafe if it was auto-cleared or resolved after t* − T_man (Eq. 9). Returned metrics: unsafe rate, auto-clear miss,
late takeover, false manoeuvre, takeover rate, MRM rate and MRMs per hour, utilisation, mean and 90th-percentile wait.

## 7. CORAL-F feasibility certificates (`coral/feasibility.py`)

`simulate_f(..., cert, mode, online)` extends the queue simulator. When a TAKEOVER request i arrives at time t_i:

1. fluid backlog wait W_i^0 = [Σ_m (f_m − t_i)^+ + Σ_{j queued} s_j] / M with nominal service time s_i (Eq. 32);
2. resolution certificate U_i = q_R (W_i^0 + s_i) (Eq. 33);
3. deadline certificate L_i = t̂_i − T_man − q_D(b_i), b_i the bin of t̂_i (Eq. 34);
4. action (Eq. 35), selected by `mode`:
   - `"full"` (CORAL-F): if U_i > L_i the request is rerouted to AVOID at once; otherwise its timeout becomes
     min(T_out, L_i) (certified timeout);
   - `"route"`: rerouting only; `"timeout"`: certified timeout only (ablations).

`calibrate_certificate(decisions, d, rng_seed, gamma=0.005, n_iter=3, n_bins=2, delta_R=0.1)`:

- π̂_T = share of D2 hazards in the takeover band; δ_D = γ / π̂_T (Eq. 36);
- bin edges = quantiles of t̂ over the band hazards (B = 2); q_D(b) = conformal (1 − δ_D) quantile of
  e = t̂ − t* within each bin (Mondrian; `conformal_quantile` uses the ⌈(n+1)(1−δ)⌉-th order statistic);
- q_R = conformal (1 − δ_R) quantile of R_j / (W_j^0 + s_j) over D2 requests, recomputed three times with the queue
  simulated under the current certificate (policy-consistent calibration).

Theorem 2 needs only δ_D: a queued hazard is resolved by its certified timeout, so it is late only if the deadline
bound fails. Online variant (`online=True`, Eq. 38): q_D(b) += η_D (1[t* − T_man < L] − δ_D) with η_D = 5 s on
hazard labels revealed after 50 later arrivals; log q_R += η_R (1[R > U] − δ_R) with η_R = 0.1 when a request is
resolved. Ablation `static_wait` replaces the live backlog by the calibration wait quantile W_q.

`run_feasibility.py` evaluates SCRC-global, CORAL, CORAL-L, CORAL-F, CORAL-F-online and four ablations on the test
set and the shifted sets, a frontier over α ∈ {0.5, 1, 1.5, 2, 3, 4}%, an audit run (certificates computed, no
action) for lateness recall, and a stream from the in-distribution test set into AIS dropout.

## 8. Metrics and statistics

Fleet metrics as in Sect. 6 above; total manoeuvres = AVOID decisions plus MRMs on non-hazards. Predictor metrics:
AUROC, AUPRC, Brier score, ECE (15 bins), NLL. Mean ± SD over five seeds; paired bootstrap of per-hazard unsafe
indicators (10,000 resamples in `analysis_v3.py`, 2,000 in `aggregate_feas.py`); sign of the paired difference per
seed; matched-cost comparisons by recalibrating at several α (`frontier.py`, `run_feasibility.py`).

## 9. Table and figure map

| Paper item | Produced by | Output |
|---|---|---|
| Figs. 1-3 | `figures_system.py` | `figures/fig1_architecture.png`, `fig2_pipeline.png`, `fig3_decision_timing.png` |
| Fig. 4 | `fig_ais_map.py` | `figures_ais/fig9_ais_map.png` |
| Tables 3-12, Figs. 5-8 | `aggregate.py` | `results*/summary_tables.md`, `figures*/fig4_calibration.png`, `fig5_alpha_sweep.png`, `fig6_operators.png`, `fig8_ood.png` |
| Fig. 9 | `fig_online_v2.py` | `figures/fig8_online_fleet.png` |
| Fig. 10 | `fig_ais.py` | `figures_ais/fig9_ais_replay.png` |
| Table 13, 15, Sect. 8.7 | `analysis_v3.py` | `results*/analysis_v3.md` |
| Table 14, Fig. 11 | `frontier.py` | `results*/frontier.json`, `frontier_summary.md`, `figures/fig11_frontier.png` |
| Tables 16-17 | `run_feasibility.py`, `aggregate_feas.py` | `results*/feas_tables.md`, `feas_summary.json` |
| Figs. 12-13 | `fig_feas.py` | `figures/fig12_feas_frontier.png`, `fig13_feas_recall.png` |

## 10. Compute

Pure NumPy. One sandbox seed (data, three five-member ensembles, all evaluations) takes about 5 min on two CPU
cores, one AIS seed about 15 min, CORAL-F post hoc a few seconds per seed. Inference costs 0.03-0.04 ms per
assessment.
