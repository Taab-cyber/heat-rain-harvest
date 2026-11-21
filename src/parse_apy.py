"""Phase 3 (step 1): parse DES APY exports (wide HTML tables) into one long table.

Input : data/raw/apy/apy_<state>.xls   (HTML <table>, despite the .xls name)
Output: data/interim/apy_long.parquet  one row per state x district x year x crop x season
Columns: state, district, year (start of agri year, int), crop, season,
         area_ha, production, production_unit, yield_reported

Raw files are never modified. "<State>_Total" rows are dropped (they are
state sums, not districts). Rows where area and production are both missing
are dropped: in the wide layout an empty cell means "crop not grown/reported".
"""
import re

import pandas as pd

from src.config import INTERIM, RAW

NUM_PREFIX = re.compile(r"^\s*\d+\.\s*")   # "1. Punjab" -> "Punjab"


def parse_file(path) -> pd.DataFrame:
    tables = pd.read_html(path, flavor="lxml")   # read_html expands rowspan/colspan
    wide = tables[0]
    if wide.shape[1] < 4:                        # "No Data Found" page
        return pd.DataFrame()
    ids = wide.iloc[:, :3].copy()
    ids.columns = ["state", "district", "year"]
    long_parts = []
    # columns come in triplets: (crop, season, Area|Production|Yield)
    for j in range(3, wide.shape[1], 3):
        crop, season, _ = wide.columns[j]
        prod_label = wide.columns[j + 1][2]       # e.g. "Production (Tonnes)" / "(Bales)"
        part = ids.copy()
        part["crop"], part["season"] = crop, season
        part["area_ha"] = pd.to_numeric(wide.iloc[:, j], errors="coerce")
        part["production"] = pd.to_numeric(wide.iloc[:, j + 1], errors="coerce")
        part["yield_reported"] = pd.to_numeric(wide.iloc[:, j + 2], errors="coerce")
        m = re.search(r"\((.*)\)", str(prod_label))
        part["production_unit"] = m.group(1) if m else str(prod_label)  # keep raw label if no "(unit)"
        long_parts.append(part)
    df = pd.concat(long_parts, ignore_index=True)
    df = df.dropna(subset=["area_ha", "production"], how="all")
    for c in ("state", "district"):
        df[c] = df[c].astype(str).str.replace(NUM_PREFIX, "", regex=True).str.strip()
    df = df[~df["district"].str.contains("_Total", case=False)]
    df["year"] = df["year"].str.slice(0, 4).astype(int)   # "1997 - 1998" -> 1997
    return df


def main() -> None:
    frames = [parse_file(p) for p in sorted((RAW / "apy").glob("apy_*.xls"))]
    df = pd.concat([f for f in frames if len(f)], ignore_index=True)
    out = INTERIM / "apy_long.parquet"
    df.to_parquet(out, index=False)
    print(f"rows={len(df):,}  states={df.state.nunique()}  districts={df[['state','district']].drop_duplicates().shape[0]}  "
          f"years={df.year.min()}-{df.year.max()}  crops={df.crop.nunique()}")
    for crop in ("Wheat", "Rice"):
        s = df[df.crop == crop]
        dy = s[["state", "district", "year"]].drop_duplicates().shape[0]
        print(f"{crop}: rows={len(s):,} district-years={dy:,} seasons={sorted(s.season.unique())}")
    print(f"saved {out}")


if __name__ == "__main__":
    main()
