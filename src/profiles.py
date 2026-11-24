"""Phase 7: one row per district - climate exposure, yield behaviour, irrigation.

Two blocks:
  climate profile  (available for EVERY Census-2011 unit with weather, even if it grows no wheat):
      mean March hot days, mean March tmax, mean season tmin, mean season rain, rain CV,
      and the year-to-year sd of March hot days (how variable the heat is)
  wheat profile    (only districts with >= MIN_YEARS years in the wheat analysis sample):
      mean yield, yield trend (kg/ha/yr), anomaly sd (volatility), share of loss years,
      heat sensitivity = slope of relative anomaly on own-mean-deviation of tmin (per +1 C),
      mean irrigation share

All statistics here use 1997-2017 only (TRAIN_LAST_YEAR), so anything later built on these
profiles (risk zones, labels, feature choices) never looks at the 2018-2022 test years.
"""
import numpy as np
import pandas as pd

from src.config import PROCESSED, TRAIN_LAST_YEAR

MIN_YEARS = 15


def _slope(x: pd.Series, y: pd.Series) -> float:
    ok = x.notna() & y.notna()
    if ok.sum() < 10 or x[ok].std() == 0:
        return np.nan
    return float(np.polyfit(x[ok], y[ok], 1)[0])


def climate_profile() -> pd.DataFrame:
    f = pd.read_parquet(PROCESSED / "features_wheat.parquet")
    f = f[(f.year >= 1997) & (f.year <= TRAIN_LAST_YEAR)]
    g = f.groupby("unit_id")
    p = pd.DataFrame({
        "hot_days_mean": g.mar_hot_days_35.mean(),
        "hot_days_sd": g.mar_hot_days_35.std(),
        "mar_tmax_mean": g.mar_tmax_mean.mean(),
        "tmin_mean": g.tmin_mean.mean(),
        "rain_mean": g.rain_total.mean(),
        "rain_cv": g.rain_total.std() / g.rain_total.mean().where(g.rain_total.mean() > 0),
    })
    return p.dropna()


def wheat_profile() -> pd.DataFrame:
    m = pd.read_parquet(PROCESSED / "model_wheat.parquet")
    m = m[m.in_sample & (m.year <= TRAIN_LAST_YEAR)].copy()
    m["tmin_dev"] = m.tmin_mean - m.groupby("unit_id").tmin_mean.transform("mean")
    rows = {}
    for uid, g in m.groupby("unit_id"):
        if len(g) < MIN_YEARS:
            continue
        rows[uid] = {
            "n_years": len(g),
            "yield_mean": g.yield_t_ha.mean(),
            "yield_trend_kg": _slope(g.year.astype(float), g.yield_t_ha) * 1000,
            "anom_sd": g.yield_rel_anom.std(),
            "loss_share": g.yield_loss.mean(),
            "heat_sens": _slope(g.tmin_dev, g.yield_rel_anom),          # relative yield change per +1 C
            "irr_mean": g.irr_share.mean(),
            "state_id": g.state_id.iloc[0], "d_name": g.d_name.iloc[0],
        }
    return pd.DataFrame.from_dict(rows, orient="index").rename_axis("unit_id")


def build() -> pd.DataFrame:
    p = climate_profile().join(wheat_profile(), how="left")
    out = PROCESSED / "district_profiles.parquet"
    p.to_parquet(out)
    print(f"climate profiles: {len(p)} units; with wheat profile: {p.yield_mean.notna().sum()}; saved {out}")
    return p


if __name__ == "__main__":
    build()
