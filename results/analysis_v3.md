## Paired bootstrap of unsafe-rate difference (pp), 10,000 resamples, stratified by seed
| A - B | mean diff | 95% CI | P(diff >= 0) |
|---|---|---|---|
| CORAL-L - SCRC-global | -0.52 | [-0.62, -0.42] | 0.0000 |
| CORAL-L - LTT-help | 0.59 | [0.49, 0.70] | 1.0000 |
| CORAL - SCRC-global | -0.35 | [-0.46, -0.24] | 0.0000 |
| CORAL-L - CORAL | -0.17 | [-0.22, -0.12] | 0.0000 |

hazards per seed: [6052, 6171, 6007, 6016, 6047]

## Lateness proxy validity (pooled over seeds; CORAL budget thresholds)
te: actually late 58, flagged by proxy 233, actually-late flagged 49 -> recall 0.845, precision 0.210
ais_dropout: actually late 795, flagged by proxy 256, actually-late flagged 164 -> recall 0.206, precision 0.641

## Calibration size (D1 samples): test auto-clear miss %, share of draws above alpha, SD of lam_lo per regime
| n1 | miss mean | miss SD | P(miss > alpha) | SD lam LEO | SD lam GEO | SD lam DEG | miss LEO | miss GEO | miss DEG |
|---|---|---|---|---|---|---|---|---|---|
| 250 | 0.75 | 1.04 | 0.11 | 0.086 | 0.000 | 0.000 | 1.15 | 0.00 | 0.00 |
| 500 | 1.08 | 0.76 | 0.12 | 0.068 | 0.007 | 0.000 | 1.64 | 0.06 | 0.00 |
| 1000 | 1.60 | 0.55 | 0.21 | 0.049 | 0.054 | 0.000 | 1.89 | 1.48 | 0.00 |
| 2000 | 1.88 | 0.46 | 0.38 | 0.040 | 0.043 | 0.056 | 2.04 | 1.75 | 1.16 |
| 4000 | 1.94 | 0.20 | 0.41 | 0.022 | 0.022 | 0.034 | 2.08 | 1.87 | 1.19 |
| 6000 | 1.92 | 0.00 | 0.20 | 0.000 | 0.000 | 0.000 | 2.05 | 1.92 | 1.08 |

## Online update bounds (online_L_budget stream)
| regime | hazards T | |avg upd err - alpha| | bound | takeover - beta | bound |
|---|---|---|---|---|---|
| 0 | 2748 | 0.07 (max 0.16) | 1.86 | -0.55 (max 1.84) | 5.51 |
| 1 | 1048 | 0.10 (max 0.22) | 4.87 | 0.04 (max 1.49) | 14.25 |
| 2 | 411 | 0.34 (max 0.47) | 12.43 | -0.96 (max 0.52) | 36.10 |

LTT thresholds: [(0.03, 0.12), (0.02, 0.07), (0.02, 0.07), (0.02, 0.08), (0.04, 0.18)] grid N=3876