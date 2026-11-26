"""Phase 10: link the long-run warming (1951-2025) to harvests.

1. Warming already felt in each crop season: change in the season-mean night temperature (tmin)
   between the 1951-1980 and 1996-2025 normals, per district (wheat: Nov-Mar; rice: Jun-Oct).
2. Implied yield effect of that warming = warming x the robust fixed-effects night-heat coefficient
   (Phase 8, `phase8/robustness_<crop>.csv`, main specification). This is a back-of-envelope estimate:
   it assumes the 1997-2022 sensitivity also held earlier and ignores adaptation and CO2 effects.
3. Do districts that warmed faster have slower yield growth? Spearman correlation between district
   warming rate (Sen's slope, 1951-2025) and district yield trend (1997-2022, kg/ha per year).
Outputs: data/processed/climate/harvest_link_<crop>.csv, harvest_link_summary.csv
"""
import numpy as np
import pandas as pd
from scipy import stats

from src.climate_trends import trend
from src.config import PROCESSED

OUT = PROCESSED / "climate"
SEASONS = {"Wheat": ([11, 12, 1, 2, 3], "wheat"), "Rice (monsoon)": ([6, 7, 8, 9, 10], "rice_monsoon")}


def season_tmin(dm: pd.DataFrame, months: list[int]) -> pd.DataFrame:
    s = dm[dm.month.isin(months)].copy()
    s["season"] = s.year
    if 11 in months:      # wheat: Nov-Dec of Y + Jan-Mar of Y+1 -> season Y (sowing year, as in features.py / APY)
        s["season"] = np.where(s.month >= 11, s.year, s.year - 1)
    g = s.groupby(["district_id", "season"]).agg(tmin=("tmin", "mean"), n=("tmin", "size")).reset_index()
    return g[g.n == len(months)]


def main() -> None:
    dm = pd.read_parquet(OUT / "district_monthly.parquet")
    summ = []
    for crop, (months, key) in SEASONS.items():
        st = season_tmin(dm, months)
        old = st[st.season.between(1951, 1980)].groupby("district_id").tmin.mean()
        new = st[st.season.between(1996, 2025)].groupby("district_id").tmin.mean()
        rate = st.groupby("district_id").apply(lambda g: trend(g.season, g.tmin)["sen_per_decade"], include_groups=False)
        coef = pd.read_csv(PROCESSED / "phase8" / f"robustness_{key}.csv").iloc[0]
        b, lo, hi = coef["effect per +1C night temp"], coef["ci_low"], coef["ci_high"]
        m = pd.read_parquet(PROCESSED / f"model_{key}.parquet")
        m = m[m.in_sample]
        ytr = m.groupby("unit_id").apply(lambda g: np.polyfit(g.year, g.yield_t_ha, 1)[0] * 1000 if g.year.nunique() >= 10 else np.nan,
                                         include_groups=False).rename("yield_trend_kg_per_yr")
        area = m.groupby("unit_id").area_ha.mean().rename("area_ha")
        t = pd.DataFrame({"warming_c": new - old, "warming_rate_c_per_decade": rate}).join(ytr, how="inner").join(area)
        t["implied_yield_effect_pct"] = t.warming_c * b * 100
        t.rename_axis("district_id").reset_index().to_csv(OUT / f"harvest_link_{key}.csv", index=False)
        wts = t.area_ha
        wm = np.average(t.warming_c, weights=wts)
        rho, p = stats.spearmanr(t.warming_rate_c_per_decade, t.yield_trend_kg_per_yr, nan_policy="omit")
        summ.append({"crop": crop, "districts": len(t),
                     "season_night_warming_c_area_weighted": wm,
                     "implied_yield_effect_pct": wm * b * 100,
                     "implied_ci_low_pct": wm * lo * 100, "implied_ci_high_pct": wm * hi * 100,
                     "spearman_warming_rate_vs_yield_trend": rho, "p": p})
    S = pd.DataFrame(summ)
    S.to_csv(OUT / "harvest_link_summary.csv", index=False)
    print(S.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
