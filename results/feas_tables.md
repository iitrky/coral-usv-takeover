## results

### In-distribution test
| Method | Unsafe % | Late % | FM % | Total man. % | Takeover % |
|---|---|---|---|---|---|
| SCRC-global | 2.50 ± 0.26 | 0.52 ± 0.17 | 10.48 ± 1.21 | 14.82 ± 1.31 | 13.10 ± 0.56 |
| CORAL | 2.15 ± 0.29 | 0.23 ± 0.09 | 12.22 ± 0.99 | 14.26 ± 0.94 | 13.02 ± 0.15 |
| CORAL-L | 1.98 ± 0.18 | 0.06 ± 0.04 | 15.30 ± 1.87 | 16.77 ± 1.52 | 9.85 ± 2.60 |
| CORAL-F | 1.95 ± 0.20 | 0.03 ± 0.02 | 16.74 ± 1.05 | 16.76 ± 1.04 | 9.47 ± 0.38 |
| CORAL-F-online | 1.96 ± 0.21 | 0.04 ± 0.03 | 16.62 ± 0.98 | 16.64 ± 0.98 | 9.56 ± 0.44 |
| F w/o routing (cert. timeout only) | 1.97 ± 0.22 | 0.05 ± 0.04 | 12.22 ± 0.99 | 16.07 ± 1.04 | 13.02 ± 0.15 |
| F w/o cert. timeout (routing only) | 1.95 ± 0.20 | 0.03 ± 0.02 | 16.74 ± 1.05 | 16.74 ± 1.05 | 9.47 ± 0.38 |
| F w/o live queue state | 1.95 ± 0.21 | 0.03 ± 0.02 | 16.83 ± 1.04 | 16.88 ± 1.02 | 9.38 ± 0.39 |
| F w/o Mondrian deadline bins | 1.94 ± 0.21 | 0.01 ± 0.01 | 18.27 ± 0.80 | 18.29 ± 0.80 | 8.19 ± 0.83 |

### Shift: ais_dropout
| Method | Unsafe % | Late % | FM % | Total man. % | Takeover % |
|---|---|---|---|---|---|
| SCRC-global | 8.86 ± 1.36 | 7.06 ± 1.22 | 15.56 ± 2.94 | 28.27 ± 3.07 | 23.25 ± 1.23 |
| CORAL | 8.41 ± 2.20 | 6.75 ± 2.19 | 18.48 ± 2.04 | 26.44 ± 3.19 | 23.50 ± 1.16 |
| CORAL-L | 2.92 ± 1.66 | 1.25 ± 1.80 | 24.22 ± 4.46 | 27.23 ± 3.18 | 17.14 ± 4.36 |
| CORAL-F | 1.85 ± 0.21 | 0.18 ± 0.06 | 25.55 ± 1.76 | 25.59 ± 1.76 | 17.19 ± 0.69 |
| CORAL-F-online | 1.82 ± 0.24 | 0.16 ± 0.07 | 25.69 ± 1.76 | 25.78 ± 1.77 | 17.05 ± 0.60 |
| F w/o routing (cert. timeout only) | 2.45 ± 0.16 | 0.78 ± 0.27 | 18.48 ± 2.04 | 26.49 ± 2.50 | 23.50 ± 1.16 |
| F w/o cert. timeout (routing only) | 1.85 ± 0.21 | 0.18 ± 0.06 | 25.56 ± 1.74 | 25.56 ± 1.74 | 17.18 ± 0.70 |
| F w/o live queue state | 2.18 ± 0.12 | 0.51 ± 0.27 | 23.73 ± 1.43 | 26.16 ± 2.18 | 18.85 ± 1.21 |
| F w/o Mondrian deadline bins | 1.85 ± 0.11 | 0.18 ± 0.16 | 26.34 ± 1.61 | 26.35 ± 1.62 | 16.16 ± 1.38 |

### Shift: link_degradation
| Method | Unsafe % | Late % | FM % | Total man. % | Takeover % |
|---|---|---|---|---|---|
| SCRC-global | 3.91 ± 1.00 | 2.13 ± 0.68 | 10.06 ± 1.42 | 20.31 ± 0.80 | 13.28 ± 0.84 |
| CORAL | 1.66 ± 0.32 | 0.21 ± 0.03 | 21.00 ± 3.48 | 22.85 ± 3.56 | 8.33 ± 0.23 |
| CORAL-L | 1.49 ± 0.34 | 0.03 ± 0.03 | 23.35 ± 3.88 | 24.37 ± 3.92 | 6.18 ± 1.33 |
| CORAL-F | 1.46 ± 0.34 | 0.01 ± 0.02 | 24.45 ± 3.59 | 24.47 ± 3.59 | 5.71 ± 0.10 |
| CORAL-F-online | 1.46 ± 0.34 | 0.01 ± 0.02 | 24.44 ± 3.53 | 24.46 ± 3.54 | 5.72 ± 0.16 |
| F w/o routing (cert. timeout only) | 1.48 ± 0.36 | 0.02 ± 0.02 | 21.00 ± 3.48 | 24.11 ± 3.58 | 8.33 ± 0.23 |
| F w/o cert. timeout (routing only) | 1.46 ± 0.34 | 0.01 ± 0.02 | 24.45 ± 3.59 | 24.45 ± 3.59 | 5.71 ± 0.10 |
| F w/o live queue state | 1.46 ± 0.34 | 0.01 ± 0.02 | 24.34 ± 3.57 | 24.45 ± 3.58 | 5.77 ± 0.21 |
| F w/o Mondrian deadline bins | 1.46 ± 0.34 | 0.01 ± 0.02 | 25.29 ± 3.85 | 25.31 ± 3.86 | 4.97 ± 0.62 |

### Shift: rough_sea
| Method | Unsafe % | Late % | FM % | Total man. % | Takeover % |
|---|---|---|---|---|---|
| SCRC-global | 3.71 ± 0.66 | 1.31 ± 0.30 | 11.04 ± 1.92 | 16.79 ± 2.05 | 15.25 ± 0.80 |
| CORAL | 2.87 ± 0.51 | 0.62 ± 0.22 | 13.66 ± 1.54 | 15.98 ± 1.41 | 14.95 ± 1.20 |
| CORAL-L | 2.41 ± 0.40 | 0.15 ± 0.13 | 17.17 ± 3.00 | 18.76 ± 2.69 | 11.40 ± 2.39 |
| CORAL-F | 2.36 ± 0.44 | 0.10 ± 0.05 | 18.40 ± 1.30 | 18.43 ± 1.31 | 11.14 ± 1.17 |
| CORAL-F-online | 2.34 ± 0.43 | 0.08 ± 0.04 | 18.49 ± 1.26 | 18.52 ± 1.27 | 11.05 ± 1.18 |
| F w/o routing (cert. timeout only) | 2.47 ± 0.46 | 0.21 ± 0.10 | 13.66 ± 1.54 | 17.69 ± 1.30 | 14.95 ± 1.20 |
| F w/o cert. timeout (routing only) | 2.36 ± 0.44 | 0.10 ± 0.05 | 18.40 ± 1.30 | 18.40 ± 1.30 | 11.14 ± 1.17 |
| F w/o live queue state | 2.39 ± 0.44 | 0.13 ± 0.05 | 18.33 ± 1.15 | 18.46 ± 1.14 | 11.18 ± 1.26 |
| F w/o Mondrian deadline bins | 2.34 ± 0.43 | 0.08 ± 0.04 | 19.93 ± 1.31 | 19.94 ± 1.30 | 9.82 ± 1.37 |

### Certificate coverage (CORAL-F, ID test)
cov_R 0.901±0.019, cov_D 0.934±0.020, target 1-delta = 0.926
  ais_dropout: cov_R 0.947, cov_D 0.874
  link_degradation: cov_R 0.906, cov_D 0.935
  rough_sea: cov_R 0.913, cov_D 0.880

### Lateness recall of the certificate (audit, no routing), pooled over seeds
  te: 54/69 = 78.3%
  ais_dropout: 806/818 = 98.5%
  link_degradation: 24/25 = 96.0%
  rough_sea: 57/75 = 76.0%

### Paired bootstrap (ID test), CORAL-F − X, unsafe pp
  vs SCRC-global: -0.55 [-0.65, -0.45], lower in 5/5 seeds
  vs CORAL: -0.20 [-0.25, -0.16], lower in 5/5 seeds
  vs CORAL-L: -0.03 [-0.07, -0.00], lower in 4/5 seeds

### Frontier (mean over seeds): alpha -> unsafe %, total manoeuvre %
  te CORAL: [(0.005, np.float64(0.53), np.float64(37.4)), (0.01, np.float64(1.12), np.float64(23.7)), (0.015, np.float64(1.73), np.float64(17.3)), (0.02, np.float64(2.15), np.float64(14.3)), (0.03, np.float64(3.74), np.float64(9.3)), (0.04, np.float64(5.7), np.float64(7.0))]
  te CORAL-F: [(0.005, np.float64(0.52), np.float64(38.5)), (0.01, np.float64(1.06), np.float64(25.5)), (0.015, np.float64(1.62), np.float64(19.8)), (0.02, np.float64(1.95), np.float64(16.8)), (0.03, np.float64(2.86), np.float64(12.8)), (0.04, np.float64(4.02), np.float64(10.4))]
  ais_dropout CORAL: [(0.005, np.float64(0.19), np.float64(51.9)), (0.01, np.float64(2.12), np.float64(37.5)), (0.015, np.float64(6.02), np.float64(30.7)), (0.02, np.float64(8.41), np.float64(26.4)), (0.03, np.float64(16.71), np.float64(19.0)), (0.04, np.float64(21.74), np.float64(14.2))]
  ais_dropout CORAL-F: [(0.005, np.float64(0.18), np.float64(52.7)), (0.01, np.float64(0.63), np.float64(37.9)), (0.015, np.float64(1.25), np.float64(30.0)), (0.02, np.float64(1.85), np.float64(25.6)), (0.03, np.float64(4.09), np.float64(19.4)), (0.04, np.float64(7.27), np.float64(15.9))]

### Stream ID -> AIS dropout
  static: unsafe_post 1.73 ± 0.24, late_post 0.07 ± 0.02, fm_post 23.96 ± 1.52
  online: unsafe_post 1.75 ± 0.26, late_post 0.08 ± 0.03, fm_post 24.10 ± 1.48