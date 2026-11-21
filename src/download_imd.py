"""Phase 2: download IMD gridded daily data with imdlib.

Variables
- rain : 0.25 deg daily rainfall (mm)
- tmax : 1.0 deg daily maximum temperature (deg C)
- tmin : 1.0 deg daily minimum temperature (deg C)

Usage (from project root, env `hrh` active):
    python -m src.download_imd                 # all vars, START_YEAR..END_YEAR+1
    python -m src.download_imd --vars tmin --start 1997 --end 1998

Why END_YEAR + 1: the agricultural year 2022-23 has its rabi season
(Nov 2022 - Apr 2023) partly in calendar 2023, so we need 2023 weather too.

imdlib skips files that already exist, so the script is safe to re-run
after an interrupted download.
"""
import argparse
import time

import imdlib as imd

from src.config import RAW_IMD, START_YEAR, END_YEAR


def download(var: str, start: int, end: int, retries: int = 3) -> None:
    for year in range(start, end + 1):
        for attempt in range(1, retries + 1):
            try:
                # yearwise -> one file per year, e.g. data/raw/imd/rain/1997.grd
                imd.get_data(var, year, year, fn_format="yearwise", file_dir=str(RAW_IMD))
                break
            except Exception as exc:  # network errors from the IMD server
                print(f"[{var} {year}] attempt {attempt} failed: {exc}")
                time.sleep(10 * attempt)
        else:
            raise RuntimeError(f"Could not download {var} {year} after {retries} tries")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vars", nargs="+", default=["tmax", "tmin", "rain"])
    ap.add_argument("--start", type=int, default=START_YEAR)
    ap.add_argument("--end", type=int, default=END_YEAR + 1)
    args = ap.parse_args()
    for var in args.vars:
        download(var, args.start, args.end)
    print("done")


if __name__ == "__main__":
    main()
