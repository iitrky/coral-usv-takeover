#!/usr/bin/env bash
# Reproduce all sandbox results (and, with --ais, the real-traffic AIS replay) of the paper.
set -euo pipefail
cd "$(dirname "$0")"
python -c "from coral.model import grad_check; print('gradient check, max rel. error:', grad_check())"
for s in 0 1 2 3 4; do python run_experiments.py --seed "$s" --out results; done
python aggregate.py results
python analysis_v3.py results
for s in 0 1 2 3 4; do python run_feasibility.py --res results --seed "$s"; done
python aggregate_feas.py results
python figures_system.py
python fig_online_v2.py
if [[ "${1:-}" == "--ais" ]]; then
  for s in 0 1 2 3 4; do python run_experiments.py --seed "$s" --source ais --out results_ais; done
  python aggregate.py results_ais
  python analysis_v3.py results_ais
  for s in 0 1 2 3 4; do python run_feasibility.py --res results_ais --seed "$s"; done
  python aggregate_feas.py results_ais
  python fig_ais.py && python fig_ais_map.py
  python frontier.py results results_ais
  python fig_feas.py
fi
echo "done: tables in results*/summary_tables.md, analysis_v3.md, feas_tables.md; figures in figures*/"
