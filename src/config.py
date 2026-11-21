"""Project-wide paths and constants.

Every script imports paths from here so nothing is hard-coded.
ROOT is found from this file's location: src/config.py -> parent of src/.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DATA = ROOT / "data"
RAW = DATA / "raw"
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"

RAW_IMD = RAW / "imd"            # IMD gridded binaries (imdlib layout: <var>/<year>.grd)
RAW_APY = RAW / "apy"            # DES Area-Production-Yield exports (manual download)
RAW_LUS = RAW / "lus"            # DES Land Use Statistics exports (manual download)
RAW_BOUNDARIES = RAW / "boundaries"  # official district boundaries + LGD codes

REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"

# Study window. APY on the DES portal starts at agricultural year 1997-98
# and (as checked on 2026-11-21) ends at 2022-23.
START_YEAR = 1997
END_YEAR = 2022

# Train/test split used in every predictive model (time-based, no shuffling).
TRAIN_LAST_YEAR = 2017

SEED = 42

for _p in (RAW_IMD, RAW_APY, RAW_LUS, RAW_BOUNDARIES, INTERIM, PROCESSED, FIGURES):
    _p.mkdir(parents=True, exist_ok=True)
