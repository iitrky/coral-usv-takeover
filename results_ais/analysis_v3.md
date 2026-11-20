## Paired bootstrap of unsafe-rate difference (pp), 10,000 resamples, stratified by seed
| A - B | mean diff | 95% CI | P(diff >= 0) |
|---|---|---|---|
| CORAL-L - SCRC-global | -0.90 | [-1.06, -0.74] | 0.0000 |
| CORAL-L - LTT-help | 0.58 | [0.43, 0.74] | 1.0000 |
| CORAL - SCRC-global | -0.89 | [-1.05, -0.73] | 0.0000 |
| CORAL-L - CORAL | -0.01 | [-0.02, 0.00] | 0.3731 |

hazards per seed: [3750, 3750, 3750, 3750, 3750]

## Lateness proxy validity (pooled over seeds; CORAL budget thresholds)
te: actually late 10, flagged by proxy 17, actually-late flagged 7 -> recall 0.700, precision 0.412
ais_dropout: actually late 787, flagged by proxy 12, actually-late flagged 8 -> recall 0.010, precision 0.667

## Calibration size (D1 samples): test auto-clear miss %, share of draws above alpha, SD of lam_lo per regime
| n1 | miss mean | miss SD | P(miss > alpha) | SD lam LEO | SD lam GEO | SD lam DEG | miss LEO | miss GEO | miss DEG |
|---|---|---|---|---|---|---|---|---|---|
| 250 | 0.17 | 0.68 | 0.02 | 0.044 | 0.000 | 0.000 | 0.25 | 0.00 | 0.00 |
| 500 | 0.97 | 0.89 | 0.11 | 0.060 | 0.000 | 0.000 | 1.49 | 0.00 | 0.00 |
| 1000 | 1.66 | 0.55 | 0.25 | 0.037 | 0.056 | 0.000 | 2.02 | 1.37 | 0.00 |
| 2000 | 1.83 | 0.45 | 0.33 | 0.027 | 0.039 | 0.032 | 2.15 | 1.49 | 0.64 |
| 4000 | 1.96 | 0.22 | 0.44 | 0.013 | 0.020 | 0.028 | 2.17 | 1.72 | 1.19 |
| 6000 | 2.05 | 0.00 | 0.60 | 0.000 | 0.000 | 0.000 | 2.27 | 1.79 | 1.24 |

## Online update bounds (online_L_budget stream)
| regime | hazards T | |avg upd err - alpha| | bound | takeover - beta | bound |
|---|---|---|---|---|---|
| 0 | 1385 | 0.22 (max 0.34) | 3.68 | 0.99 (max 1.39) | 5.51 |
| 1 | 539 | 0.23 (max 0.55) | 9.47 | 0.23 (max 0.70) | 14.30 |
| 2 | 215 | 0.56 (max 1.17) | 23.91 | -1.80 (max -1.19) | 35.97 |

LTT thresholds: [(0.04, 0.15), (0.03, 0.13), (0.03, 0.13), (0.05, 0.2), (0.04, 0.19)] grid N=3876