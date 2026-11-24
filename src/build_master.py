"""Phase 3 (step 9): master table for wheat and rice, one row per unit x year x crop.

- Seasons are combined: area and production summed over all seasons of the crop,
  yield recomputed (D6). If any season row of that unit-year was flagged as an
  implausible yield (D11), the unit-year yield is left missing (conservative).
- Irrigation share of the crop = crop-wise irrigated area (LUS) / crop area (APY).
  LUS and APY are collected separately, so the ratio can exceed 1; values up to 1.1
  are clipped to 1, values above 1.1 are set missing and flagged (D12).
- District-level irrigation intensity = net irrigated / net sown area (LUS).
- Weather is NOT joined here: crop-season weather features are built in Phase 4
  and joined on (unit_id, year).

Output: data/processed/master_wheat_rice.parquet
"""
import pandas as pd

from src.boundaries import load_pc11_districts
from src.build_crop_panel import TRIPURA_UNIT
from src.config import PROCESSED

CROPS = {"Wheat": "wheat_irrigated_ha", "Rice": "rice_irrigated_ha", "Rice (monsoon)": "rice_irrigated_ha"}
# note: LUS irrigated rice covers all seasons, so irr_share for "Rice (monsoon)" is approximate


def main() -> None:
    crop = pd.read_parquet(PROCESSED / "crop_panel_pc11.parquet")
    lus = pd.read_parquet(PROCESSED / "lus_panel_pc11.parquet")
    crop = crop[crop.crop.isin(CROPS) & (crop.production_unit == "Tonnes")]
    # Extra "crop": monsoon-season rice only (kharif, autumn/aus, winter/aman), so the target
    # matches the Jun-Oct weather window; boro/rabi/summer rice is excluded (D19).
    monsoon = crop[(crop.crop == "Rice") & crop.season.isin(["Kharif", "Autumn", "Winter"])].assign(crop="Rice (monsoon)")
    crop = pd.concat([crop, monsoon], ignore_index=True)

    # rows usable for yield = both area and production reported and not flagged
    ok = crop["yield_clean"].notna()
    crop = crop.assign(area_ok=crop.area_ha.where(ok), prod_ok=crop.production.where(ok))
    m = crop.groupby(["unit_id", "year", "crop"], as_index=False).agg(
        area_ha=("area_ha", "sum"), production_t=("production", "sum"),
        area_ok=("area_ok", "sum"), prod_ok=("prod_ok", "sum"),
        n_seasons=("season", "nunique"), seasons=("season", lambda s: "+".join(sorted(s))),
        any_flag=("yield_flag", "any"), any_split_parent=("any_split_parent", "any"),
    )
    m["yield_t_ha"] = (m.prod_ok / m.area_ok.where(m.area_ok > 0)).where(~m.any_flag)
    m = m.drop(columns=["area_ok", "prod_ok"]).rename(columns={"any_flag": "yield_flag"})

    # irrigation
    lus = lus.assign(net_irr_intensity=lus.net_irrigated_ha / lus.net_sown_ha.where(lus.net_sown_ha > 0))
    m = m.merge(lus, on=["unit_id", "year"], how="left")
    irr_cols = sorted(set(CROPS.values()))
    m["crop_irrigated_ha"] = [r[CROPS[c]] for c, (_, r) in zip(m.crop, m[irr_cols].iterrows())]
    share = m.crop_irrigated_ha / m.area_ha.where(m.area_ha > 0)
    m["irr_share_flag"] = share > 1.1
    m["irr_share"] = share.clip(upper=1.0).mask(m.irr_share_flag)
    m = m.drop(columns=sorted(set(CROPS.values())))

    # names
    names = load_pc11_districts()[["district_id", "state_id", "d_name"]].rename(columns={"district_id": "unit_id"})
    m = m.merge(names, on="unit_id", how="left")
    m.loc[m.unit_id == TRIPURA_UNIT, ["d_name", "state_id"]] = ["Tripura (all districts)", 16]

    out = PROCESSED / "master_wheat_rice.parquet"
    m.to_parquet(out, index=False)
    print(f"master rows: {len(m):,}  columns: {m.shape[1]}")
    for c in CROPS:
        s = m[m.crop == c]
        print(f"  {c}: unit-years {len(s):,}, units {s.unit_id.nunique()}, with yield {s.yield_t_ha.notna().sum():,}, "
              f"with irr_share {s.irr_share.notna().sum():,}, irr_share>1.1 flagged {int(s.irr_share_flag.sum())}")
    print(f"saved {out}")


if __name__ == "__main__":
    main()
