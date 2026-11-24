"""Phase 3 (step 8): Land Use Statistics on fixed Census-2011 district units.

Same unit rule as the crop panel (Tripura = one unit, 9016). Every LUS column is
an area in hectares, so units are formed by summing. A unit-year value is
missing (not 0) when none of its source districts reported that column
(sum with min_count=1).

Output: data/processed/lus_panel_pc11.parquet (unit_id, year, + hectare columns)
"""
import pandas as pd

from src.build_crop_panel import TRIPURA_UNIT
from src.config import INTERIM, PROCESSED

KEEP = {
    "Net Area Sown": "net_sown_ha",
    "Cropped Area": "gross_cropped_ha",          # portal label; = net sown + area sown more than once
    "Net Irrigated Area | Total": "net_irrigated_ha",
    "Gross Irrigated Area | Total": "gross_irrigated_ha",
    "Net Irrigated Area | Canal | Total": "net_irr_canal_ha",
    "Net Irrigated Area | Tank": "net_irr_tank_ha",
    "Net Irrigated Area | Well | Tubewell": "net_irr_tubewell_ha",
    "Net Irrigated Area | Well | Other Well": "net_irr_otherwell_ha",
    "Net Irrigated Area | Other Source": "net_irr_other_ha",
    "rice_irrigated_ha": "rice_irrigated_ha",
    "wheat_irrigated_ha": "wheat_irrigated_ha",
}


def main() -> None:
    lus = pd.read_parquet(INTERIM / "lus_wide.parquet")
    missing = [c for c in KEEP if c not in lus.columns]
    if missing:
        raise KeyError(f"expected LUS columns not found: {missing}")
    dm = pd.read_csv(INTERIM / "district_map.csv")
    dm = dm[dm.source == "lus"][["state", "district", "pc11_district_code"]]
    df = lus[["state", "district", "year", *KEEP]].rename(columns=KEEP).merge(dm, on=["state", "district"], how="left")
    df["unit_id"] = df["pc11_district_code"]
    df.loc[df["state"] == "Tripura", "unit_id"] = TRIPURA_UNIT
    lost = df["unit_id"].isna()
    print(f"LUS district-years without a 2011 unit (dropped): {int(lost.sum()):,} "
          f"({sorted(df.loc[lost, 'district'].unique())})")
    df = df[~lost].copy()
    df["unit_id"] = df["unit_id"].astype(int)
    cols = list(KEEP.values())
    g = df.groupby(["unit_id", "year"])[cols].sum(min_count=1).reset_index()
    out = PROCESSED / "lus_panel_pc11.parquet"
    g.to_parquet(out, index=False)
    print(f"LUS panel: {len(g):,} unit-years, {g.unit_id.nunique()} units, {g.year.min()}-{g.year.max()}")
    for c in cols:
        print(f"  {c}: non-missing {g[c].notna().sum():,}")
    print(f"saved {out}")


if __name__ == "__main__":
    main()
