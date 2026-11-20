## results_ais

### In-distribution test
| Method | Unsafe % | Late % | FM % | Total man. % | Takeover % |
|---|---|---|---|---|---|
| SCRC-global | 2.98 ± 0.77 | 0.86 ± 0.50 | 7.43 ± 1.40 | 9.64 ± 1.23 | 13.23 ± 0.60 |
| CORAL | 2.09 ± 0.29 | 0.04 ± 0.05 | 8.75 ± 0.96 | 9.74 ± 0.94 | 13.41 ± 0.48 |
| CORAL-L | 2.08 ± 0.29 | 0.03 ± 0.05 | 9.01 ± 0.95 | 9.97 ± 0.93 | 13.21 ± 0.47 |
| CORAL-F | 2.05 ± 0.25 | 0.00 ± 0.00 | 11.74 ± 0.78 | 11.74 ± 0.78 | 10.58 ± 0.64 |
| CORAL-F-online | 2.05 ± 0.25 | 0.00 ± 0.00 | 11.70 ± 0.79 | 11.70 ± 0.79 | 10.63 ± 0.63 |
| F w/o routing (cert. timeout only) | 2.05 ± 0.26 | 0.01 ± 0.01 | 8.75 ± 0.96 | 11.60 ± 0.75 | 13.41 ± 0.48 |
| F w/o cert. timeout (routing only) | 2.05 ± 0.25 | 0.00 ± 0.00 | 11.74 ± 0.78 | 11.74 ± 0.78 | 10.58 ± 0.64 |
| F w/o live queue state | 2.05 ± 0.25 | 0.00 ± 0.00 | 11.71 ± 0.81 | 11.73 ± 0.80 | 10.59 ± 0.66 |
| F w/o Mondrian deadline bins | 2.05 ± 0.25 | 0.00 ± 0.00 | 12.75 ± 0.75 | 12.75 ± 0.75 | 9.28 ± 0.29 |

### Shift: ais_dropout
| Method | Unsafe % | Late % | FM % | Total man. % | Takeover % |
|---|---|---|---|---|---|
| SCRC-global | 11.28 ± 3.15 | 9.07 ± 2.41 | 12.02 ± 2.78 | 21.71 ± 2.40 | 22.10 ± 1.38 |
| CORAL | 13.16 ± 2.98 | 11.16 ± 2.75 | 13.46 ± 1.83 | 19.29 ± 1.29 | 23.42 ± 1.39 |
| CORAL-L | 11.53 ± 3.76 | 9.53 ± 3.59 | 13.74 ± 1.78 | 17.80 ± 1.45 | 23.20 ± 1.36 |
| CORAL-F | 2.07 ± 0.43 | 0.07 ± 0.09 | 18.11 ± 1.31 | 18.19 ± 1.23 | 18.91 ± 0.63 |
| CORAL-F-online | 2.03 ± 0.51 | 0.03 ± 0.06 | 18.61 ± 1.24 | 18.70 ± 1.20 | 18.49 ± 0.68 |
| F w/o routing (cert. timeout only) | 2.24 ± 0.38 | 0.24 ± 0.21 | 13.46 ± 1.83 | 19.76 ± 1.46 | 23.42 ± 1.39 |
| F w/o cert. timeout (routing only) | 2.07 ± 0.43 | 0.07 ± 0.09 | 18.14 ± 1.32 | 18.14 ± 1.32 | 18.89 ± 0.60 |
| F w/o live queue state | 2.23 ± 0.40 | 0.23 ± 0.19 | 16.75 ± 1.68 | 19.55 ± 1.29 | 20.19 ± 1.22 |
| F w/o Mondrian deadline bins | 2.07 ± 0.45 | 0.07 ± 0.09 | 18.97 ± 1.18 | 18.97 ± 1.17 | 17.86 ± 0.42 |

### Shift: link_degradation
| Method | Unsafe % | Late % | FM % | Total man. % | Takeover % |
|---|---|---|---|---|---|
| SCRC-global | 8.24 ± 1.60 | 6.07 ± 1.08 | 7.52 ± 1.11 | 15.47 ± 0.90 | 13.15 ± 0.77 |
| CORAL | 1.85 ± 0.53 | 0.07 ± 0.07 | 15.56 ± 1.88 | 16.30 ± 1.91 | 8.83 ± 0.70 |
| CORAL-L | 1.79 ± 0.51 | 0.00 ± 0.00 | 16.60 ± 2.02 | 17.22 ± 2.02 | 8.04 ± 0.61 |
| CORAL-F | 1.79 ± 0.51 | 0.00 ± 0.00 | 17.82 ± 1.82 | 17.82 ± 1.82 | 6.78 ± 0.48 |
| CORAL-F-online | 1.79 ± 0.51 | 0.00 ± 0.00 | 17.79 ± 1.84 | 17.79 ± 1.84 | 6.80 ± 0.51 |
| F w/o routing (cert. timeout only) | 1.79 ± 0.51 | 0.00 ± 0.00 | 15.56 ± 1.88 | 17.67 ± 1.81 | 8.83 ± 0.70 |
| F w/o cert. timeout (routing only) | 1.79 ± 0.51 | 0.00 ± 0.00 | 17.82 ± 1.82 | 17.82 ± 1.82 | 6.78 ± 0.48 |
| F w/o live queue state | 1.79 ± 0.51 | 0.00 ± 0.00 | 17.57 ± 1.86 | 17.68 ± 1.79 | 6.96 ± 0.51 |
| F w/o Mondrian deadline bins | 1.79 ± 0.51 | 0.00 ± 0.00 | 18.22 ± 1.89 | 18.22 ± 1.89 | 6.17 ± 0.73 |

### Shift: rough_sea
| Method | Unsafe % | Late % | FM % | Total man. % | Takeover % |
|---|---|---|---|---|---|
| SCRC-global | 3.97 ± 1.30 | 1.73 ± 1.01 | 8.34 ± 1.63 | 10.86 ± 1.45 | 13.93 ± 0.88 |
| CORAL | 2.17 ± 0.66 | 0.05 ± 0.07 | 10.06 ± 1.37 | 10.97 ± 1.33 | 13.94 ± 0.91 |
| CORAL-L | 2.13 ± 0.64 | 0.01 ± 0.03 | 10.29 ± 1.35 | 11.18 ± 1.30 | 13.76 ± 0.89 |
| CORAL-F | 2.12 ± 0.62 | 0.00 ± 0.00 | 12.87 ± 1.22 | 12.88 ± 1.21 | 11.25 ± 0.76 |
| CORAL-F-online | 2.12 ± 0.62 | 0.00 ± 0.00 | 12.90 ± 1.21 | 12.90 ± 1.20 | 11.22 ± 0.74 |
| F w/o routing (cert. timeout only) | 2.12 ± 0.62 | 0.00 ± 0.00 | 10.06 ± 1.37 | 12.78 ± 1.26 | 13.94 ± 0.91 |
| F w/o cert. timeout (routing only) | 2.12 ± 0.62 | 0.00 ± 0.00 | 12.87 ± 1.22 | 12.87 ± 1.22 | 11.25 ± 0.76 |
| F w/o live queue state | 2.12 ± 0.62 | 0.00 ± 0.00 | 12.83 ± 1.25 | 12.87 ± 1.24 | 11.27 ± 0.78 |
| F w/o Mondrian deadline bins | 2.12 ± 0.62 | 0.00 ± 0.00 | 13.93 ± 0.85 | 13.93 ± 0.85 | 9.87 ± 0.36 |

### Certificate coverage (CORAL-F, ID test)
cov_R 0.906±0.012, cov_D 0.974±0.017, target 1-delta = 0.958
  ais_dropout: cov_R 0.945, cov_D 0.926
  link_degradation: cov_R 0.927, cov_D 0.960
  rough_sea: cov_R 0.897, cov_D 0.947

### Lateness recall of the certificate (audit, no routing), pooled over seeds
  te: 7/7 = 100.0%
  ais_dropout: 834/837 = 99.6%
  link_degradation: 5/5 = 100.0%
  rough_sea: 4/4 = 100.0%

### Paired bootstrap (ID test), CORAL-F − X, unsafe pp
  vs SCRC-global: -0.93 [-1.08, -0.77], lower in 5/5 seeds
  vs CORAL: -0.04 [-0.07, -0.01], lower in 2/5 seeds
  vs CORAL-L: -0.03 [-0.06, -0.01], lower in 2/5 seeds

### Frontier (mean over seeds): alpha -> unsafe %, total manoeuvre %
  te CORAL: [(0.005, np.float64(0.54), np.float64(28.7)), (0.01, np.float64(1.09), np.float64(15.1)), (0.015, np.float64(1.53), np.float64(12.5)), (0.02, np.float64(2.09), np.float64(9.7)), (0.03, np.float64(2.9), np.float64(7.4)), (0.04, np.float64(3.82), np.float64(5.7))]
  te CORAL-F: [(0.005, np.float64(0.54), np.float64(29.1)), (0.01, np.float64(1.09), np.float64(16.0)), (0.015, np.float64(1.51), np.float64(13.9)), (0.02, np.float64(2.05), np.float64(11.7)), (0.03, np.float64(2.77), np.float64(9.6)), (0.04, np.float64(3.63), np.float64(7.9))]
  ais_dropout CORAL: [(0.005, np.float64(0.55), np.float64(39.8)), (0.01, np.float64(3.08), np.float64(24.8)), (0.015, np.float64(6.08), np.float64(21.7)), (0.02, np.float64(13.16), np.float64(19.3)), (0.03, np.float64(18.48), np.float64(16.6)), (0.04, np.float64(23.29), np.float64(14.2))]
  ais_dropout CORAL-F: [(0.005, np.float64(0.55), np.float64(40.1)), (0.01, np.float64(1.07), np.float64(25.5)), (0.015, np.float64(1.52), np.float64(21.8)), (0.02, np.float64(2.07), np.float64(18.2)), (0.03, np.float64(2.83), np.float64(15.2)), (0.04, np.float64(3.93), np.float64(12.6))]

### Stream ID -> AIS dropout
  static: unsafe_post 2.00 ± 0.52, late_post 0.00 ± 0.00, fm_post 16.86 ± 1.65
  online: unsafe_post 2.00 ± 0.52, late_post 0.00 ± 0.00, fm_post 16.85 ± 1.57