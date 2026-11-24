"""Phase 3 (step 3): parse DES Land Use Statistics exports into one table.

Input : data/raw/lus/lus_<state>.xls  (HTML table, 5-level header, "Vertical Year")
Output: data/interim/lus_wide.parquet  one row per state x district x year
        data/interim/lus_columns.csv   original 5-level header -> flat column name

Layout of the raw table: a row carrying State + District names, followed by one
row per agricultural year where State/District are blank -> forward-fill them.
"-" in a cell means "not reported" and is kept as missing (NaN), never as 0.
Values are hectares (Unit = Hectare was selected on the portal).
"""
import re

import pandas as pd

from src.config import INTERIM, RAW


def flat_name(levels) -> str:
    """Join the distinct, non-'Unnamed' header levels: ('Net Irrigated Area','Canals','Government') -> 'Net Irrigated Area | Canals | Government'."""
    parts = []
    for lv in levels:
        lv = str(lv).strip()
        if lv.startswith("Unnamed") or (parts and parts[-1] == lv):
            continue
        parts.append(lv)
    return " | ".join(parts)


def parse_file(path):
    wide = pd.read_html(path, flavor="lxml")[0]
    cols, seen = [], {}
    for c in wide.columns:                       # repeated flat names get " #2", " #3" (in header order)
        n = flat_name(c)
        seen[n] = seen.get(n, 0) + 1
        cols.append(n if seen[n] == 1 else f"{n} #{seen[n]}")
    mapping = pd.DataFrame({"levels": [" || ".join(map(str, c)) for c in wide.columns], "column": cols})
    wide.columns = cols
    wide = wide.rename(columns={"State": "state", "District": "district", "Year": "year"})
    wide[["state", "district"]] = wide[["state", "district"]].ffill()   # names sit on a row above the years
    wide = wide[wide["year"].astype(str).str.match(r"^\d{4}-\d{4}$")].copy()
    wide["year"] = wide["year"].str.slice(0, 4).astype(int)
    for c in wide.columns.difference(["state", "district", "year"]):
        wide[c] = pd.to_numeric(wide[c].astype(str).str.replace(",", ""), errors="coerce")  # "-" -> NaN
    wide["state"] = wide["state"].str.strip()
    wide["district"] = wide["district"].str.strip()
    return wide, mapping


def main() -> None:
    frames, maps = [], []
    for p in sorted((RAW / "lus").glob("lus_*.xls")):
        w, m = parse_file(p)
        frames.append(w)
        maps.append(m)
    df = pd.concat(frames, ignore_index=True)
    # Duplicate flat names can occur (e.g. two "Total" sub-columns); make them unique, in order.
    if df.columns.duplicated().any():
        seen = {}
        new = []
        for c in df.columns:
            seen[c] = seen.get(c, 0) + 1
            new.append(c if seen[c] == 1 else f"{c} #{seen[c]}")
        df.columns = new
    n_tot = df["state"].str.startswith("Total of").sum()
    df = df[~df["state"].str.startswith("Total of")].copy()     # state-sum rows, not districts
    print(f"dropped {n_tot:,} 'Total of <State>' rows")

    # Derived crop-wise irrigated area (DECISIONS D10). The portal labels irrigated rice
    # by the traditional seasons Autumn/Winter/Summer (sometimes Kharif/Rabi) plus Total.
    # Use the portal's Total when present, otherwise the sum of whatever season columns
    # are present; if none are present, leave missing (never 0).
    for crop, out in (("Rice", "rice_irrigated_ha"), ("Wheat", "wheat_irrigated_ha")):
        base = f"Food Crop | Cereals & Millets | {crop}"
        total_cols = [c for c in df.columns if c.startswith(base) and c.split(" | ")[-1].startswith("Total")]
        part_cols = [c for c in df.columns if (c == base or c.startswith(base + " | ")) and c not in total_cols]
        total = df[total_cols].bfill(axis=1).iloc[:, 0] if total_cols else pd.Series(float("nan"), index=df.index)
        parts = df[part_cols].sum(axis=1, min_count=1) if part_cols else pd.Series(float("nan"), index=df.index)
        df[out] = total.fillna(parts)
        print(f"{out}: from total cols {total_cols}, part cols {part_cols}; non-missing={df[out].notna().sum():,}")

    df.to_parquet(INTERIM / "lus_wide.parquet", index=False)
    pd.concat(maps).drop_duplicates().to_csv(INTERIM / "lus_columns.csv", index=False)
    print(f"rows={len(df):,} cols={df.shape[1]} states={df.state.nunique()} "
          f"districts={df[['state','district']].drop_duplicates().shape[0]} years={df.year.min()}-{df.year.max()}")
    key = re.compile(r"Net Irrigated Area$|Gross Irrigated Area$|Net Area Sown|Total Cropped Area|Rice|Wheat|Total Irrigated Area")
    for c in df.columns:
        if key.search(c):
            print(f"  {c!r}: non-missing={df[c].notna().sum():,}")


if __name__ == "__main__":
    main()
