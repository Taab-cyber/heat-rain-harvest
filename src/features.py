"""Phase 4: crop-season weather features + yield detrending.

Agricultural year Y (APY "2021 - 2022" -> Y = 2021).
  Wheat (rabi):  1 Nov Y .. 31 Mar Y+1   (sown Nov, harvested Mar-Apr; the window ends
                 on 31 March so the same features serve the pre-harvest forecast)
  Rice (kharif): 1 Jun Y .. 31 Oct Y     (monsoon season; dry spells use Jun-Sep)
(DECISIONS D13)

Daily mean temperature T = (tmax + tmin) / 2.
  GDD  = sum over days of  max(0, min(T, T_upper) - T_base)
         wheat: T_base 0 C, T_upper 30 C ; rice: T_base 10 C, T_upper 35 C
  EDD  = extreme degree days = sum of max(0, tmax - T_hot)   (wheat 34 C, rice 35 C)
  hot days = number of days with tmax > 35 C (wheat: in March only, the grain-filling month)
  rain = season total (mm); rainy days = days with rain >= 2.5 mm (IMD definition)
  rain CV = std / mean of monthly rain totals within the season (variability)
  longest dry spell = longest run of consecutive days with rain < 2.5 mm (rice, Jun-Sep)
A season value is set missing if more than 10% of its days have no data.

Detrending (per unit, per crop):  yield_t = a + b * year + e_t
  - `trend_full`, `yield_anom`, `yield_rel_anom`: fit on all years. DESCRIPTIVE ONLY (EDA,
    statistics); it uses future years, so it must NOT be used to evaluate forecasts.
  - `detrend_train_only()`: fits on years <= TRAIN_LAST_YEAR and extrapolates; use this in
    Phase 8 so no test-year information leaks into the features or the target.

Outputs: data/processed/features_{wheat,rice}.parquet, data/processed/model_{wheat,rice}.parquet
"""
import numpy as np
import pandas as pd

from src.boundaries import load_pc11_districts
from src.build_crop_panel import TRIPURA_UNIT
from src.config import INTERIM, PROCESSED, TRAIN_LAST_YEAR

RAINY_MM = 2.5
MIN_AREA_HA = 1000          # D14
LOSS_THRESHOLD = 0.10       # yield loss = more than 10% below trend (D14)
SEASONS = {
    "Wheat": dict(start=(11, 1), end=(3, 31), crosses_year=True, t_base=0.0, t_upper=30.0, t_hot=34.0),
    "Rice": dict(start=(6, 1), end=(10, 31), crosses_year=False, t_base=10.0, t_upper=35.0, t_hot=35.0),
}


# ---------------------------------------------------------------- climate input
def load_daily() -> pd.DataFrame:
    """Wide daily table: unit_id, date, tmax, tmin, rain (Tripura's 4 districts combined)."""
    parts = []
    for var in ("tmax", "tmin", "rain"):
        d = pd.read_parquet(INTERIM / f"climate_{var}_daily.parquet").rename(columns={"value": var})
        parts.append(d.set_index(["district_id", "date"]))
    df = pd.concat(parts, axis=1).reset_index().rename(columns={"district_id": "unit_id"})
    return add_tripura_unit(df)


def add_tripura_unit(df: pd.DataFrame) -> pd.DataFrame:
    """Tripura = one unit (D6c): area-weighted mean of its 2011 districts' daily weather."""
    g = load_pc11_districts().to_crs("EPSG:6933")
    trip = g[g.state_id == 16].assign(area=lambda x: x.geometry.area)[["district_id", "area"]]
    w = trip.set_index("district_id")["area"]
    t = df[df.unit_id.isin(w.index)].copy()
    t["w"] = t.unit_id.map(w)
    out = {}
    for v in ("tmax", "tmin", "rain"):
        ok = t[v].notna()
        num = (t[v] * t.w).where(ok).groupby(t.date).sum()
        den = t.w.where(ok).groupby(t.date).sum()
        out[v] = num / den.where(den > 0)
    comp = pd.DataFrame(out).reset_index().assign(unit_id=TRIPURA_UNIT)
    return pd.concat([df, comp[df.columns]], ignore_index=True)


# ---------------------------------------------------------------- season features
def longest_run(below: np.ndarray) -> int:
    """Longest run of consecutive True values (e.g. dry days)."""
    best = cur = 0
    for b in below:
        cur = cur + 1 if b else 0
        best = max(best, cur)
    return best


def season_mask(dates: pd.Series, crop: str) -> pd.Series:
    """Agricultural year each date belongs to for this crop, or NaN if outside the window."""
    s = SEASONS[crop]
    m, y = dates.dt.month, dates.dt.year
    if s["crosses_year"]:                                      # Nov-Dec of Y, Jan-Mar of Y+1
        year = np.where(m >= s["start"][0], y, np.where(m <= s["end"][0], y - 1, np.nan))
    else:
        year = np.where((m >= s["start"][0]) & (m <= s["end"][0]), y, np.nan)
    return pd.Series(year, index=dates.index)


def crop_features(daily: pd.DataFrame, crop: str) -> pd.DataFrame:
    s = SEASONS[crop]
    d = daily.copy()
    d["year"] = season_mask(d["date"], crop)
    d = d.dropna(subset=["year"])
    d["year"] = d["year"].astype(int)
    d["T"] = (d.tmax + d.tmin) / 2
    d["gdd"] = (d["T"].clip(upper=s["t_upper"]) - s["t_base"]).clip(lower=0)
    d["edd"] = (d.tmax - s["t_hot"]).clip(lower=0)
    d["hot35"] = (d.tmax > 35).astype(float).where(d.tmax.notna())
    d["rainy"] = (d.rain >= RAINY_MM).astype(float).where(d.rain.notna())
    d["month"] = d.date.dt.month
    keys = ["unit_id", "year"]

    g = d.groupby(keys)
    f = pd.DataFrame({
        "n_days": g.size(),
        "temp_missing_share": g.tmax.apply(lambda x: x.isna().mean()),
        "tmax_mean": g.tmax.mean(), "tmin_mean": g.tmin.mean(),
        "gdd": g.gdd.sum(min_count=1), "edd": g.edd.sum(min_count=1),
        "rain_total": g.rain.sum(min_count=1), "rainy_days": g.rainy.sum(min_count=1),
        "rain_missing_share": g.rain.apply(lambda x: x.isna().mean()),
    })
    monthly = d.groupby(keys + ["month"]).rain.sum(min_count=1)
    mg = monthly.groupby(level=keys)
    f["rain_cv_monthly"] = mg.std() / mg.mean().where(mg.mean() > 0)

    if crop == "Wheat":
        mar = d[d.month == 3].groupby(keys)
        f["mar_tmax_mean"] = mar.tmax.mean()
        f["mar_hot_days_35"] = mar.hot35.sum(min_count=1)
        f["edd_mar"] = mar.edd.sum(min_count=1)
        f["rain_nov_jan"] = d[d.month.isin([11, 12, 1])].groupby(keys).rain.sum(min_count=1)
        # Phase 8 feature iteration (D19): February heat and grain-filling heat above 30 C
        f["feb_tmax_mean"] = d[d.month == 2].groupby(keys).tmax.mean()
        fm = d[d.month.isin([2, 3])].assign(e30=lambda x: (x.tmax - 30).clip(lower=0))
        f["edd30_feb_mar"] = fm.groupby(keys).e30.sum(min_count=1)
    else:
        jjas = d[d.month.isin([6, 7, 8, 9])].sort_values(keys + ["date"])
        f["rain_jun_sep"] = jjas.groupby(keys).rain.sum(min_count=1)
        f["longest_dry_spell"] = jjas.groupby(keys).rain.apply(lambda x: longest_run((x < RAINY_MM).to_numpy()))
        f["hot_days_35"] = g.hot35.sum(min_count=1)
        # Phase 8 feature iteration (D19): monsoon rain by month (June = sowing/transplanting)
        for mo, name in ((6, "rain_jun"), (7, "rain_jul"), (8, "rain_aug"), (9, "rain_sep")):
            f[name] = d[d.month == mo].groupby(keys).rain.sum(min_count=1)

    # incomplete seasons -> missing (D13)
    temp_cols = [c for c in f.columns if c.startswith(("tmax", "tmin", "gdd", "edd", "mar_", "hot"))]
    rain_cols = [c for c in f.columns if c.startswith(("rain", "rainy", "longest"))]
    f.loc[f.temp_missing_share > 0.10, temp_cols] = np.nan
    f.loc[f.rain_missing_share > 0.10, rain_cols] = np.nan
    expected = 151 if crop == "Wheat" else 153                    # days in the window (non-leap)
    f.loc[f.n_days < expected * 0.9, temp_cols + rain_cols] = np.nan   # season not fully in the data
    f = f.reset_index()
    if crop == "Wheat":
        # Preceding monsoon (Jun-Sep of year Y) recharges soil and groundwater for the rabi crop
        # sown in November of Y: known before sowing, so valid for a pre-harvest forecast (D19).
        mon = daily[daily.date.dt.month.isin([6, 7, 8, 9])].assign(year=lambda x: x.date.dt.year)
        prev = mon.groupby(["unit_id", "year"]).rain.agg(["sum", lambda x: x.isna().mean()])
        prev.columns = ["prev_monsoon_rain", "miss"]
        prev.loc[prev.miss > 0.10, "prev_monsoon_rain"] = np.nan
        f = f.merge(prev[["prev_monsoon_rain"]].reset_index(), on=["unit_id", "year"], how="left")
    return f


# ---------------------------------------------------------------- detrending
def _fit_line(years: np.ndarray, y: np.ndarray):
    ok = ~np.isnan(y)
    if ok.sum() < 8:                                               # too few years for a trend
        return np.nan, np.nan
    b, a = np.polyfit(years[ok], y[ok], 1)
    return a, b


def detrend_full(m: pd.DataFrame) -> pd.DataFrame:
    """Linear trend per unit on all years. Descriptive use only (uses future years)."""
    out = []
    for _, g in m.groupby("unit_id"):
        a, b = _fit_line(g.year.to_numpy(float), g.yield_t_ha.to_numpy(float))
        out.append(pd.Series(a + b * g.year, index=g.index))
    m["trend_full"] = pd.concat(out)
    m["yield_anom"] = m.yield_t_ha - m.trend_full
    m["yield_rel_anom"] = m.yield_anom / m.trend_full.where(m.trend_full > 0)
    return m


def detrend_train_only(m: pd.DataFrame, last_train_year: int = TRAIN_LAST_YEAR) -> pd.DataFrame:
    """Trend fitted on years <= last_train_year only, extrapolated to later years (no leakage)."""
    m = m.copy()
    out = []
    for _, g in m.groupby("unit_id"):
        tr = g[g.year <= last_train_year]
        a, b = _fit_line(tr.year.to_numpy(float), tr.yield_t_ha.to_numpy(float))
        out.append(pd.Series(a + b * g.year, index=g.index))
    m["trend_train"] = pd.concat(out)
    m["yield_anom_train"] = m.yield_t_ha - m.trend_train
    m["yield_rel_anom_train"] = m.yield_anom_train / m.trend_train.where(m.trend_train > 0)
    return m


# ---------------------------------------------------------------- main
def main() -> None:
    daily = load_daily()
    master = pd.read_parquet(PROCESSED / "master_wheat_rice.parquet")
    feats = {}
    for crop in SEASONS:
        feats[crop] = crop_features(daily, crop)
        feats[crop].to_parquet(PROCESSED / f"features_{crop.lower()}.parquet", index=False)
    # "Rice (monsoon)" = kharif/autumn/winter rice only, matched to the Jun-Oct window (D19)
    for crop, fkey, fname in (("Wheat", "Wheat", "wheat"), ("Rice", "Rice", "rice"), ("Rice (monsoon)", "Rice", "rice_monsoon")):
        if crop not in set(master.crop):
            continue
        f = feats[fkey]
        m = master[master.crop == crop].merge(f, on=["unit_id", "year"], how="left")
        m = detrend_full(m.sort_values(["unit_id", "year"]).reset_index(drop=True))
        # D14: analysis sample = crop area >= MIN_AREA_HA and a clean yield (tiny areas give noisy yields)
        m["in_sample"] = (m.area_ha >= MIN_AREA_HA) & m.yield_t_ha.notna()
        # yield-loss event: more than LOSS_THRESHOLD below the (descriptive) trend
        m["yield_loss"] = (m.yield_rel_anom < -LOSS_THRESHOLD).where(m.yield_rel_anom.notna())
        m.to_parquet(PROCESSED / f"model_{fname}.parquet", index=False)
        s = m[m.in_sample]
        print(f"{crop}: feature rows {len(f):,}; model rows {len(m):,}; in analysis sample {len(s):,} "
              f"({s.unit_id.nunique()} units); with all weather {s.dropna(subset=['gdd', 'rain_total']).shape[0]:,}; "
              f"yield-loss share {s.yield_loss.mean():.1%}")


if __name__ == "__main__":
    main()
