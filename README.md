# Heat, Rain & Harvest

District wheat and rice yields for India (1997-98 to 2022-23) on fixed Census 2011 districts, linked to India
Meteorological Department daily weather and DES irrigation data. The project covers statistical tests, risk zones,
forecasting models evaluated on unseen years, warming scenarios, long-run climate trends since 1901, and a Streamlit
**Crop-Climate Risk Atlas** (live: https://crop-climate-risk-atlas.streamlit.app).

MCA109 Data Science Foundation, TIET Patiala. Team: Mehtaab, Pravansh.

**Data:** every raw, intermediate and processed file is on the release page
https://github.com/Taab-cyber/heat-rain-harvest/releases/tag/data-v1 (10 zip archives, about 0.9 GB, with checksums).
Unzip them into `data/` and run `bash run_all.sh`, or start from `processed.zip` alone to rerun the analysis.

**The atlas** opens with the main results in English, Hindi or Punjabi, then lets you pick a district: risk of a bad
year (more than 10% below normal), yields by season with a likely reason for each bad year, general actions linked to
official sources (ICAR, PAU, PMFBY, PMKSY, IMD agromet, Krishi Vigyan Kendras), and a one-page PDF report. Researchers
can download a district summary and a district-year panel as CSV under For experts.

| Document | What it is |
|---|---|
| `PROGRESS.md` | current state, file and column names, row counts |
| `DECISIONS.md` | every method choice (D1-D24) with alternatives and reasons |
| `LEARNING.md` | per-phase explanation and exam theory |
| `VIVA.md` | viva questions with model answers, tough questions |
| `reports/course_report.md` | course report |
| `reports/paper/paper.tex` | IEEE-style paper draft (+ `references.bib`) |
| `reports/tableau/TABLEAU.md` | how to build the Tableau Public dashboard |

---

## 1. Environment (once)
WSL Ubuntu, Miniconda.
```bash
cd ~/projects/heat-rain-harvest
conda env create -f environment.yml      # creates env "hrh"
conda activate hrh
```

## 2. Raw data (once; raw files are never edited)
| Data | How | Saved to |
|---|---|---|
| IMD tmax/tmin 1997-2023 | `python -m src.download_imd --vars tmax tmin` | `data/raw/imd/{tmax,tmin}/` |
| IMD rain 1997-2023 | the scripted download fails on IMD's server; download each year from https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_Bin.html, then run `python -m src.collect_imd_rain` (exact size check) | `data/raw/imd/rain/` |
| DES APY (all states, all crops, 1997-98 to 2022-23) | browser export, one file per state: see `docs/MANUAL_DOWNLOADS.md`; `python -m src.collect_apy_batch --kind apy` files them | `data/raw/apy/` |
| DES Land Use Statistics | same, `--kind lus` | `data/raw/lus/` |
| Census 2011 district + sub-district polygons | SHRUG "Open Polygons" (PC11 District / Subdistrict, SHP) from https://www.devdatalab.org/shrug_download/ | `data/raw/boundaries/shrug-pc11{dist,subdist}-poly-shp.zip` |
| LGD all districts, all sub-districts | https://lgdirectory.gov.in -> Download Directory (captcha) | `data/raw/boundaries/lgd_all_{districts,subdistricts}_*.xlsx` |

## 3. Rebuild everything (in this order)
```bash
conda activate hrh
python -m src.parse_apy              # APY HTML tables -> data/interim/apy_long.parquet
python -m src.parse_lus              # LUS HTML tables -> data/interim/lus_wide.parquet
python -m src.district_inventory     # district names and years
python -m src.post2011_parents       # 2011 parents of new districts (via tehsils)
python -m src.district_map           # names -> Census 2011 district codes
python -m src.build_crop_panel       # crops on fixed 2011 districts (388,399 rows)
python -m src.build_lus_panel        # irrigation on fixed 2011 districts
python -m src.build_master           # wheat / rice / monsoon-rice master table
python -m src.climate_to_district    # grid -> district daily weather (slow: ~10-20 min)
python -m src.features               # season features, detrending, model tables
python -m pytest tests/ -q           # 10 tests: synthetic checks + leakage on real data
python -m src.profiles               # district profiles for Phase 7
python -m src.run_phase8             # models, classifiers, robustness, scenarios (~15 min)
python -m src.scenario_uncertainty   # bootstrap intervals for scenarios (~10 min)
# Phase 10 (long-run climate; needs IMD tmax/tmin 1951-2025 and rain 1901-2025 in data/raw/imd/)
python -m src.download_imd --vars tmax tmin --start 1951 --end 2025
python -m src.download_imd --vars rain --start 1901 --end 2025
python -m src.climate_to_district --vars tmax tmin --start 1951 --end 2025 --tag longrun   # ~20 min
python -m src.climate_to_district --vars rain --start 1901 --end 2025 --tag longrun        # ~40 min
python -m src.climate_trends         # warming by year/season/month/week/day, hot days, winters
python -m src.monsoon_trends         # monsoon 1901-2025
python -m src.climate_harvest        # warming so far -> implied yield effect
python -m src.harvest_factors        # previous-season yield, tubewell share
python -m src.loss_patterns          # loss seasons by region and their weather
python -m src.build_db               # app/atlas.sqlite + app/districts.geojson
python -m src.export_tableau         # reports/tableau/*.csv
```
Or run everything with `bash run_all.sh` (add `--skip-longrun` to skip Phase 10).

## 4. Notebooks (classic Jupyter: `jupyter notebook`, open in `notebooks/`)
| Notebook | Phase |
|---|---|
| `01_data_check.ipynb` | 1: first look at IMD data |
| `05_eda.ipynb` | 5: EDA and maps |
| `06_statistics.ipynb` | 6: inferential statistics |
| `07_patterns.ipynb` | 7: PCA, MDS, t-SNE, clustering, label propagation, feature selection |
| `08_models.ipynb` | 8: models, forecast, scenarios (reads saved results) |
| `10_loss_patterns.ipynb` | loss seasons by region, weather in loss vs normal seasons |
| `09_climate_trends.ipynb` | 10: warming 1951-2025, winters, monsoon 1901-2025, harvest link, harvest factors |

Notebooks are generated by `notebooks/builders/make_0X_*.py`; to re-run one from scratch:
`python notebooks/builders/make_06_statistics.py && jupyter nbconvert --to notebook --execute --inplace notebooks/06_statistics.ipynb`.
Figures are saved to `reports/figures/`.

## 5. The app
```bash
streamlit run app/app.py             # then open http://localhost:8501
# Live: https://crop-climate-risk-atlas.streamlit.app  (deployment steps: docs/DEPLOY.md)
```

## 6. The paper
No LaTeX is installed in WSL. Upload `reports/paper/paper.tex`, `reports/paper/references.bib` and the
`reports/figures/` folder to Overleaf (IEEEtran is built in), or install TeX Live and run
`pdflatex paper && bibtex paper && pdflatex paper && pdflatex paper` in `reports/paper/`.
References were checked against publisher records on 2026-11-24 (DOIs in references.bib).

## 7. Reproducibility notes
- Random seed 42 everywhere (`src/config.py`).
- Train <= 2017, test 2018-2022; trends, scaling, district means and tuning use training years only (`tests/`).
- `data/` and derived app/Tableau files are git-ignored and rebuilt by the scripts above.
