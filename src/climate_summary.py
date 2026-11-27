"""Phase 10 (atlas tables): winter change per district and a state-level climate summary.

Inputs (all written earlier by src.climate_trends and src.climate_harvest):
  data/processed/climate/district_winters.parquet   cool days, first and last cool day per district and winter
  data/processed/climate/district_trends.parquet    Sen's slope per district (annual tmax, tmin, tmean)
  data/processed/climate/harvest_link_wheat.csv     wheat-season night warming and implied yield effect
Outputs:
  data/processed/climate/district_winter_change.csv  one row per district
  data/processed/climate/state_climate_summary.csv   one row per state (area-weighted)

Periods are the same as everywhere else in Phase 10 (D20): old normal 1952-1981 (the first full winters of the
temperature record; a winter is labelled by the year it ends), recent 1996-2025.
"""
import numpy as np
import pandas as pd

from src.boundaries import load_pc11_districts
from src.config import PROCESSED

OUT = PROCESSED / "climate"
OLD, NEW = (1952, 1981), (1996, 2025)


def district_winter_change(per: pd.DataFrame) -> pd.DataFrame:
    """Mean cool days and first/last cool day per district, old normal vs recent 30 years.

    `per` has district_id, season, cool_days, first_cool_day, last_cool_day (days after 1 October).
    A positive start_shift_days means winter now starts later; a negative end_shift_days means it ends earlier.
    Winters without any cool day have no first/last day and are left out of those means.
    """
    def period_mean(lo_hi):
        p = per[per.season.between(*lo_hi)]
        return p.groupby("district_id")[["cool_days", "first_cool_day", "last_cool_day"]].mean()

    old, new = period_mean(OLD), period_mean(NEW)
    out = pd.DataFrame({
        "cool_days_then": old.cool_days, "cool_days_now": new.cool_days,
        "start_then": old.first_cool_day, "start_now": new.first_cool_day,
        "end_then": old.last_cool_day, "end_now": new.last_cool_day,
    })
    out["cool_days_change"] = out.cool_days_now - out.cool_days_then
    out["start_shift_days"] = out.start_now - out.start_then
    out["end_shift_days"] = out.end_now - out.end_then
    return out.reset_index()


def _wavg(x: pd.Series, w: pd.Series) -> float:
    ok = x.notna() & w.notna() & (w > 0)
    return float(np.average(x[ok], weights=w[ok])) if ok.any() else np.nan


def state_summary(trends: pd.DataFrame, winters: pd.DataFrame, wheat: pd.DataFrame, area: pd.Series,
                  state_of: pd.Series) -> pd.DataFrame:
    """Area-weighted state averages.

    trends:  district_id, tmax/tmin/tmean_per_decade (annual)
    winters: output of district_winter_change
    wheat:   district_id, warming_c, implied_yield_effect_pct, area_ha (wheat area; the weight for wheat columns)
    area:    land area per district_id (the weight for climate columns)
    state_of: state_id per district_id
    """
    d = trends.set_index("district_id")[["tmean_per_decade", "tmax_per_decade", "tmin_per_decade"]]
    d = d.join(winters.set_index("district_id")[["cool_days_then", "cool_days_now", "start_shift_days", "end_shift_days"]])
    d = d.join(wheat.set_index("district_id")[["warming_c", "implied_yield_effect_pct", "area_ha"]])
    d["land"] = area
    d["state_id"] = state_of
    rows = []
    for sid, g in d.dropna(subset=["state_id"]).groupby("state_id"):
        r = {"state_id": int(sid), "districts": len(g)}
        for c in ("tmean_per_decade", "tmax_per_decade", "tmin_per_decade", "cool_days_then", "cool_days_now",
                  "start_shift_days", "end_shift_days"):
            r[c] = _wavg(g[c], g.land)
        r["wheat_night_warming_c"] = _wavg(g.warming_c, g.area_ha)
        r["wheat_yield_effect_pct"] = _wavg(g.implied_yield_effect_pct, g.area_ha)
        r["wheat_area_kha"] = float(g.area_ha.where(g.implied_yield_effect_pct.notna()).sum()) / 1e3
        rows.append(r)
    out = pd.DataFrame(rows)
    out["cool_days_change"] = out.cool_days_now - out.cool_days_then
    return out.sort_values("tmean_per_decade", ascending=False).reset_index(drop=True)


def main() -> None:
    per = pd.read_parquet(OUT / "district_winters.parquet")
    win = district_winter_change(per)
    win.to_csv(OUT / "district_winter_change.csv", index=False)

    trends = pd.read_parquet(OUT / "district_trends.parquet")
    trends = trends[trends.period == "annual"]
    wheat = pd.read_csv(OUT / "harvest_link_wheat.csv")
    geo = load_pc11_districts()
    eq = geo.to_crs("EPSG:6933")                      # equal-area projection, as in the climate aggregation (D20)
    area = pd.Series(eq.geometry.area.to_numpy(), index=geo.district_id.to_numpy())
    state_of = pd.Series(geo.state_id.to_numpy(), index=geo.district_id.to_numpy())
    st = state_summary(trends, win, wheat, area, state_of)
    st.to_csv(OUT / "state_climate_summary.csv", index=False)
    print(f"{len(win)} districts, {len(st)} states written")
    print(st.head(6).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
