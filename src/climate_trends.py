"""Phase 10: how fast is India warming, and how are winters changing? (IMD 1951-2025)

Input : data/interim/climate_{tmax,tmin}_longrun_daily.parquet  (district_id, date, value), from
        `python -m src.climate_to_district --vars tmax tmin --start 1951 --end 2025 --tag longrun`
Output: data/processed/climate/*.csv | *.parquet  (read by notebooks/09_climate_trends.ipynb and the app)

Methods (DECISIONS D20)
- National series = AREA-weighted mean over the 640 Census-2011 districts (big districts count more).
- Trend = Sen's slope (median of all pairwise slopes; robust to single extreme years), in C per decade,
  with the Mann-Kendall test (Kendall's tau of value vs year) for significance; OLS slope reported too.
- Baseline (normal) period = 1951-1980; recent period = 1996-2025 (two 30-year climate normals).
- Seasons (IMD convention): winter = Dec-Feb (December counted with the FOLLOWING year), pre-monsoon =
  Mar-May, monsoon = Jun-Sep, post-monsoon = Oct-Nov.
- Hot days = days with tmax >= 40 C (any month) and days with tmax >= 35 C in March (wheat grain filling).
- Cool season (winter length) = per district, days in Oct-Mar whose 7-day mean temperature is below that
  district's own 1951-1980 25th percentile of 7-day mean temperature. District-specific, so a
  Kerala "winter" is judged against Kerala's normal, not Punjab's. The season Oct(y-1)-Mar(y) is labelled y.
- Cold nights = days in Dec-Feb with tmin below the district's 1951-1980 10th percentile of Dec-Feb tmin
  (an ETCCDI-style TN10p count).
A trend is a rate over decades. Single days and weeks are compared as 30-year normals, not trended day by day.
"""
import numpy as np
import pandas as pd
from scipy import stats

from src.boundaries import load_pc11_districts
from src.config import INTERIM, PROCESSED

OUT = PROCESSED / "climate"
BASE = (1951, 1980)
RECENT = (1996, 2025)
SEASON = {12: "winter (DJF)", 1: "winter (DJF)", 2: "winter (DJF)", 3: "pre-monsoon (MAM)", 4: "pre-monsoon (MAM)",
          5: "pre-monsoon (MAM)", 6: "monsoon (JJAS)", 7: "monsoon (JJAS)", 8: "monsoon (JJAS)", 9: "monsoon (JJAS)",
          10: "post-monsoon (ON)", 11: "post-monsoon (ON)"}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# ------------------------------------------------------------------ helpers
def trend(years, values) -> dict:
    """Sen's slope and OLS slope (C per decade) + Mann-Kendall p-value."""
    y = np.asarray(years, float)
    v = np.asarray(values, float)
    ok = ~np.isnan(v)
    y, v = y[ok], v[ok]
    if len(v) < 10:
        return {"sen_per_decade": np.nan, "ols_per_decade": np.nan, "mk_p": np.nan, "n_years": len(v)}
    sen = stats.theilslopes(v, y)[0]
    ols = np.polyfit(y, v, 1)[0]
    tau, p = stats.kendalltau(y, v)
    return {"sen_per_decade": sen * 10, "ols_per_decade": ols * 10, "mk_tau": tau, "mk_p": p, "n_years": len(v)}


def area_weights() -> pd.Series:
    g = load_pc11_districts().to_crs("EPSG:6933")
    return pd.Series(g.geometry.area.to_numpy(), index=g.district_id.to_numpy(), name="area")


def wmean(df: pd.DataFrame, by: list[str], col: str, w: pd.Series) -> pd.Series:
    d = df[by + ["district_id", col]].dropna()
    d = d.assign(w=d.district_id.map(w))
    return (d[col] * d.w).groupby([d[k] for k in by]).sum() / d.w.groupby([d[k] for k in by]).sum()


def load_daily() -> pd.DataFrame:
    tx = pd.read_parquet(INTERIM / "climate_tmax_longrun_daily.parquet").rename(columns={"value": "tmax"})
    tn = pd.read_parquet(INTERIM / "climate_tmin_longrun_daily.parquet").rename(columns={"value": "tmin"})
    d = tx.merge(tn, on=["district_id", "date"], how="outer")
    d["date"] = pd.to_datetime(d["date"])
    d["year"], d["month"] = d.date.dt.year.astype("int16"), d.date.dt.month.astype("int8")
    d["tmean"] = ((d.tmax + d.tmin) / 2).astype("float32")
    return d


# ------------------------------------------------------------------ analyses
def monthly_and_annual(d: pd.DataFrame, w: pd.Series) -> dict:
    dm = d.groupby(["district_id", "year", "month"], observed=True)[["tmax", "tmin", "tmean"]].mean().reset_index()
    nat_m = pd.DataFrame({v: wmean(dm, ["year", "month"], v, w) for v in ("tmax", "tmin", "tmean")}).reset_index()
    nat_y = nat_m.groupby("year")[["tmax", "tmin", "tmean"]].mean().reset_index()        # mean of 12 months
    nat_m["season"] = nat_m.month.map(SEASON)
    nat_m["season_year"] = np.where(nat_m.month == 12, nat_m.year + 1, nat_m.year)
    nat_s = nat_m.groupby(["season", "season_year"])[["tmax", "tmin", "tmean"]].mean().reset_index()
    nat_s = nat_s[~((nat_s.season == "winter (DJF)") & ((nat_s.season_year == 1951) | (nat_s.season_year == 2026)))]

    rows = []
    for v in ("tmax", "tmin", "tmean"):
        rows.append({"period": "annual", "variable": v, **trend(nat_y.year, nat_y[v])})
        for m in range(1, 13):
            s = nat_m[nat_m.month == m]
            rows.append({"period": MONTHS[m - 1], "variable": v, **trend(s.year, s[v])})
        for sname, s in nat_s.groupby("season"):
            rows.append({"period": sname, "variable": v, **trend(s.season_year, s[v])})
    tr = pd.DataFrame(rows)
    base = nat_y[nat_y.year.between(*BASE)][["tmax", "tmin", "tmean"]].mean()
    nat_y = nat_y.assign(**{f"{v}_anom_vs_1951_80": nat_y[v] - base[v] for v in ("tmax", "tmin", "tmean")})
    return {"dm": dm, "nat_monthly": nat_m, "nat_annual": nat_y, "nat_seasonal": nat_s, "national_trends": tr}


def district_trends(dm: pd.DataFrame) -> pd.DataFrame:
    rows = []
    ann = dm.groupby(["district_id", "year"])[["tmax", "tmin", "tmean"]].mean().reset_index()
    for did, g in ann.groupby("district_id"):
        r = {"district_id": did, "period": "annual"}
        for v in ("tmax", "tmin", "tmean"):
            r[f"{v}_per_decade"] = trend(g.year, g[v])["sen_per_decade"]
        r["tmean_mk_p"] = trend(g.year, g.tmean)["mk_p"]
        rows.append(r)
    for (did, m), g in dm.groupby(["district_id", "month"]):
        r = {"district_id": did, "period": MONTHS[m - 1]}
        for v in ("tmax", "tmin", "tmean"):
            r[f"{v}_per_decade"] = trend(g.year, g[v])["sen_per_decade"]
        r["tmean_mk_p"] = trend(g.year, g.tmean)["mk_p"]
        rows.append(r)
    return pd.DataFrame(rows)


def day_and_week_normals(d: pd.DataFrame, w: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    """National mean temperature for each calendar day and week: 1951-80 normal vs 1996-2025 normal."""
    x = d[~((d.date.dt.month == 2) & (d.date.dt.day == 29))].copy()
    x["doy"] = x.date.dt.strftime("%m-%d")
    nat = wmean(x, ["year", "doy"], "tmean", w).rename("tmean").reset_index()
    old = nat[nat.year.between(*BASE)].groupby("doy").tmean.mean()
    new = nat[nat.year.between(*RECENT)].groupby("doy").tmean.mean()
    day = pd.DataFrame({"normal_1951_80": old, "normal_1996_2025": new}).reset_index()
    day["warming_c"] = day.normal_1996_2025 - day.normal_1951_80
    nat["week"] = ((pd.to_datetime("2001-" + nat.doy).dt.dayofyear - 1) // 7 + 1).clip(upper=52)
    wk = nat.groupby(["year", "week"]).tmean.mean().reset_index()
    rows = []
    for k, g in wk.groupby("week"):
        rows.append({"week": int(k),
                     "normal_1951_80": g[g.year.between(*BASE)].tmean.mean(),
                     "normal_1996_2025": g[g.year.between(*RECENT)].tmean.mean(),
                     **trend(g.year, g.tmean)})
    week = pd.DataFrame(rows)
    week["warming_c"] = week.normal_1996_2025 - week.normal_1951_80
    return day, week


def hot_days(d: pd.DataFrame, w: pd.Series) -> pd.DataFrame:
    d40 = d.assign(h40=(d.tmax >= 40).astype("int8"), m35=((d.month == 3) & (d.tmax >= 35)).astype("int8"))
    per = d40.groupby(["district_id", "year"])[["h40", "m35"]].sum().reset_index()
    out = pd.DataFrame({"days_tmax_ge40": wmean(per, ["year"], "h40", w),
                        "march_days_tmax_ge35": wmean(per, ["year"], "m35", w)}).reset_index()
    return out


def winters(d: pd.DataFrame, w: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Cool-season length and cold nights per district and season, then national means."""
    d = d.sort_values(["district_id", "date"])
    d["t7"] = d.groupby("district_id").tmean.transform(lambda s: s.rolling(7, center=True, min_periods=5).mean())
    base = d[d.year.between(*BASE)]
    thr7 = base.groupby("district_id").t7.quantile(0.25)
    djf = base[base.month.isin([12, 1, 2])]
    thr_n = djf.groupby("district_id").tmin.quantile(0.10)
    cs = d[d.month.isin([10, 11, 12, 1, 2, 3])].copy()
    cs["season"] = np.where(cs.month >= 10, cs.year + 1, cs.year)                    # Oct 2023-Mar 2024 -> 2024
    cs["cool"] = (cs.t7 < cs.district_id.map(thr7)).astype("int8")
    cs["cold_night"] = (cs.month.isin([12, 1, 2]) & (cs.tmin < cs.district_id.map(thr_n))).astype("int8")
    cs["day"] = (cs.date - pd.to_datetime((cs.season - 1).astype(str) + "-10-01")).dt.days   # days since 1 Oct
    per = cs.groupby(["district_id", "season"]).agg(
        n_days=("cool", "size"), cool_days=("cool", "sum"), cold_nights=("cold_night", "sum"),
        winter_tmin_djf=("tmin", lambda s: np.nan)).reset_index()
    first_last = cs[cs.cool == 1].groupby(["district_id", "season"]).day.agg(["min", "max"]).rename(
        columns={"min": "first_cool_day", "max": "last_cool_day"}).reset_index()
    per = per.merge(first_last, on=["district_id", "season"], how="left").drop(columns="winter_tmin_djf")
    per = per[(per.season > 1951) & (per.season < 2026) & (per.n_days >= 170)]       # complete seasons only
    nat = pd.DataFrame({c: wmean(per, ["season"], c, w) for c in ("cool_days", "cold_nights", "first_cool_day", "last_cool_day")}).reset_index()
    return per, nat


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    w = area_weights()
    d = load_daily()
    print(f"daily rows {len(d):,}, districts {d.district_id.nunique()}, years {d.year.min()}-{d.year.max()}")
    r = monthly_and_annual(d, w)
    r["nat_annual"].to_csv(OUT / "national_annual.csv", index=False)
    r["nat_monthly"].to_csv(OUT / "national_monthly.csv", index=False)
    r["nat_seasonal"].to_csv(OUT / "national_seasonal.csv", index=False)
    r["national_trends"].to_csv(OUT / "national_trends.csv", index=False)
    district_trends(r["dm"]).to_parquet(OUT / "district_trends.parquet", index=False)
    r["dm"].to_parquet(OUT / "district_monthly.parquet", index=False)
    day, week = day_and_week_normals(d, w)
    day.to_csv(OUT / "national_day_of_year.csv", index=False)
    week.to_csv(OUT / "national_week_of_year.csv", index=False)
    hd = hot_days(d, w)
    hd.to_csv(OUT / "national_hot_days.csv", index=False)
    per, nat = winters(d, w)
    per.to_parquet(OUT / "district_winters.parquet", index=False)
    nat.to_csv(OUT / "national_winters.csv", index=False)

    # records + headline numbers
    ny = r["nat_annual"]
    top = ny.sort_values("tmean", ascending=False).head(10)[["year", "tmean", "tmean_anom_vs_1951_80"]]
    top.to_csv(OUT / "record_hot_years.csv", index=False)
    rec_m = r["nat_monthly"].loc[r["nat_monthly"].groupby("month").tmean.idxmax(), ["month", "year", "tmean"]]
    rec_m.assign(month=rec_m.month.map(lambda m: MONTHS[m - 1])).to_csv(OUT / "record_hot_month_years.csv", index=False)
    tr = r["national_trends"]
    print(tr[tr.variable == "tmean"][["period", "sen_per_decade", "mk_p"]].round(3).to_string(index=False))
    print("hottest years:", top.year.tolist())
    for c in ("cool_days", "cold_nights"):
        t = trend(nat.season, nat[c])
        print(f"{c}: {t['sen_per_decade']:+.2f} per decade (MK p={t['mk_p']:.3g}); "
              f"1952-1981 mean {nat[nat.season.between(1952, 1981)][c].mean():.1f}, 1996-2025 mean {nat[nat.season.between(1996, 2025)][c].mean():.1f}")
    for c in ("days_tmax_ge40", "march_days_tmax_ge35"):
        t = trend(hd.year, hd[c])
        print(f"{c}: {t['sen_per_decade']:+.2f} days per decade (MK p={t['mk_p']:.3g})")


if __name__ == "__main__":
    main()
