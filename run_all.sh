#!/usr/bin/env bash
# Rebuild every result from the raw files in data/raw/ (raw files are never modified).
# Usage (from the project root, inside the `hrh` conda env):   bash run_all.sh [--skip-longrun]
# Total time on a laptop: about 1.5-2 hours, mostly the grid-to-district steps.
set -euo pipefail
cd "$(dirname "$0")"
step() { echo; echo "=== $* ==="; }

step "Phase 2-3: parse crop and land-use tables, harmonise districts"
python -m src.parse_apy
python -m src.parse_lus
python -m src.district_inventory
python -m src.post2011_parents
python -m src.district_map
python -m src.build_crop_panel
python -m src.build_lus_panel
python -m src.build_master

step "Phase 3: weather grid -> districts (1997-2023)"
python -m src.climate_to_district

step "Phase 4-8: features, leakage test, profiles, models, scenarios"
python -m src.features
python -m pytest tests/ -q             # synthetic unit tests + leakage test on the real data
python -m src.profiles
python -m src.run_phase8
python -m src.scenario_uncertainty

if [[ "${1:-}" != "--skip-longrun" ]]; then
  step "Phase 10: long-run climate (temperature 1951-2025, rain 1901-2025)"
  python -m src.climate_to_district --vars tmax tmin --start 1951 --end 2025 --tag longrun
  python -m src.climate_to_district --vars rain --start 1901 --end 2025 --tag longrun
  python -m src.climate_trends
  python -m src.monsoon_trends
  python -m src.climate_harvest
  python -m src.harvest_factors
fi

python -m src.loss_patterns

step "Phase 9: app database, Tableau exports, notebooks"
python -m src.build_db
python -m src.export_tableau
for b in notebooks/builders/make_*.py; do python "$b"; done
for nb in notebooks/0[5-9]_*.ipynb notebooks/10_*.ipynb; do
  jupyter nbconvert --to notebook --execute --inplace "$nb"
done

echo; echo "Done. Start the atlas with:  streamlit run app/app.py"
