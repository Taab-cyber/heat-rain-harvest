"""Phase 3 (step 7): APY on fixed Census-2011 district units.

unit_id = Census 2011 (PC11) district code, except Tripura, where all districts are
combined into one unit (unit_id 9016) because its 2012 districts have no derivable
2011 parent (DECISIONS D6c).

Aggregation rule (D6): within unit x year x crop x season x production_unit,
  area_ha    = sum of area over source districts
  production = sum of production over source districts
  yield      = production / area, computed only from rows where BOTH area and
               production are reported (so a missing production never lowers yield)
Yields are never averaged.

Output: data/processed/crop_panel_pc11.parquet
"""
import pandas as pd

from src.config import INTERIM, PROCESSED

TRIPURA_UNIT = 9016

# Physical ceilings for a *district-average* yield, t/ha (D11). Chosen well above the
# best district averages seen in the data (wheat ~5.8, rice ~5); crops not listed
# are only checked against their own district median.
YIELD_CAP_T_HA = {"Wheat": 7.0, "Rice": 8.0}


def main() -> None:
    apy = pd.read_parquet(INTERIM / "apy_long.parquet")
    dm = pd.read_csv(INTERIM / "district_map.csv")
    dm = dm[dm.source == "apy"][["state", "district", "pc11_district_code", "match_type"]]
    df = apy.merge(dm, on=["state", "district"], how="left")
    assert df["match_type"].notna().all(), "every APY name must appear in district_map"

    df["unit_id"] = df["pc11_district_code"]
    df.loc[df["state"] == "Tripura", "unit_id"] = TRIPURA_UNIT          # D6c
    lost = df["unit_id"].isna()
    print(f"APY rows without a 2011 unit (dropped): {int(lost.sum()):,}")
    df = df[~lost].copy()
    df["unit_id"] = df["unit_id"].astype(int)

    both = df["area_ha"].notna() & df["production"].notna()
    df["area_for_yield"] = df["area_ha"].where(both)
    df["prod_for_yield"] = df["production"].where(both)
    keys = ["unit_id", "year", "crop", "season", "production_unit"]
    g = df.groupby(keys, as_index=False).agg(
        area_ha=("area_ha", "sum"), production=("production", "sum"),
        area_for_yield=("area_for_yield", "sum"), prod_for_yield=("prod_for_yield", "sum"),
        n_source_districts=("district", "nunique"),
        any_split_parent=("match_type", lambda s: (s == "post2011_split_parent").any()),
    )
    g["yield"] = g["prod_for_yield"] / g["area_for_yield"].where(g["area_for_yield"] > 0)
    g = g.drop(columns=["area_for_yield", "prod_for_yield"])

    # Implausible yields (DECISIONS D11): keep the raw value, flag it, and blank `yield_clean`.
    #  (a) above a physical ceiling for a district average (t/ha), or
    #  (b) more than 3x above / below that unit's own median for the same crop and season.
    g["yield_raw"] = g["yield"]
    med = g.groupby(["unit_id", "crop", "season", "production_unit"])["yield"].transform("median")
    ratio = g["yield"] / med
    cap = g["crop"].map(YIELD_CAP_T_HA)
    g["yield_flag"] = ((g["yield"] > cap) | (ratio > 3) | (ratio < 1 / 3)).fillna(False)
    g["yield_clean"] = g["yield"].mask(g["yield_flag"])
    g = g.drop(columns=["yield"])
    print(f"flagged implausible yields: {int(g.yield_flag.sum()):,} of {g.yield_raw.notna().sum():,} "
          f"(wheat {int(g[g.crop=='Wheat'].yield_flag.sum())}, rice {int(g[g.crop=='Rice'].yield_flag.sum())})")
    out = PROCESSED / "crop_panel_pc11.parquet"
    g.to_parquet(out, index=False)

    print(f"crop panel rows (unit x year x crop x season): {len(g):,}  units={g.unit_id.nunique()}  "
          f"years={g.year.min()}-{g.year.max()}  crops={g.crop.nunique()}")
    for crop in ("Wheat", "Rice"):
        s = g[g.crop == crop]
        uy = s[["unit_id", "year"]].drop_duplicates().shape[0]
        print(f"  {crop}: rows={len(s):,} unit-years={uy:,} units={s.unit_id.nunique()} "
              f"rows with clean yield={s['yield_clean'].notna().sum():,}")
    print(f"saved {out}")


if __name__ == "__main__":
    main()
