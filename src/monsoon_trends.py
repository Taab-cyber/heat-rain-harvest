"""Phase 10: how is the monsoon changing? (IMD 0.25 deg daily rainfall, 1901-2025)

Input : data/interim/climate_rain_longrun_daily.parquet, from
        `python -m src.climate_to_district --vars rain --start 1901 --end 2025 --tag longrun`
Output: data/processed/climate/monsoon_*.csv, district_monsoon.parquet

Per district and year (monsoon = June-September, IMD's definition):
  jjas_mm          monsoon rainfall total
  annual_mm        calendar-year total
  rainy_days       days with >= 2.5 mm (IMD rainy day)
  heavy_days       days with >= 64.5 mm  (IMD "heavy rain")
  very_heavy_days  days with >= 115.6 mm (IMD "very heavy")
  extreme_days     days with >= 204.5 mm (IMD "extremely heavy")
  longest_dry      longest run of days < 2.5 mm within June-September
  deficient        jjas_mm more than 19% below the district's 1951-2000 mean (IMD's "deficient" cut-off,
                   applied here to each district's own normal)
National values are area-weighted means over districts. Trends: Sen's slope per decade + Mann-Kendall
(see src.climate_trends.trend). District-averaged rain smooths single-station extremes, so heavy-rain
day counts here are district-average counts, lower than station counts.
"""
import numpy as np
import pandas as pd

from src.climate_trends import area_weights, trend, wmean
from src.config import INTERIM, PROCESSED

OUT = PROCESSED / "climate"
NORMAL = (1951, 2000)


def longest_run(below: np.ndarray) -> int:
    best = cur = 0
    for b in below:
        cur = cur + 1 if b else 0
        best = best if best > cur else cur
    return best


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    w = area_weights()
    d = pd.read_parquet(INTERIM / "climate_rain_longrun_daily.parquet")
    d["date"] = pd.to_datetime(d.date)
    d["year"], d["month"] = d.date.dt.year.astype("int16"), d.date.dt.month.astype("int8")
    print(f"rain rows {len(d):,}, districts {d.district_id.nunique()}, years {d.year.min()}-{d.year.max()}")
    ann = d.groupby(["district_id", "year"]).value.sum(min_count=300).rename("annual_mm")
    j = d[d.month.between(6, 9)].sort_values(["district_id", "date"])
    v = j.value
    g = j.assign(rainy=(v >= 2.5), heavy=(v >= 64.5), vheavy=(v >= 115.6), ext=(v >= 204.5)).groupby(["district_id", "year"])
    per = pd.DataFrame({
        "jjas_mm": g.value.sum(min_count=110),
        "rainy_days": g.rainy.sum(), "heavy_days": g.heavy.sum(),
        "very_heavy_days": g.vheavy.sum(), "extreme_days": g.ext.sum(),
        "longest_dry": g.value.apply(lambda s: longest_run((s < 2.5).to_numpy())),
    }).join(ann).reset_index()
    normal = per[per.year.between(*NORMAL)].groupby("district_id").jjas_mm.mean()
    per["jjas_pct_of_normal"] = per.jjas_mm / per.district_id.map(normal) * 100
    per["deficient"] = (per.jjas_pct_of_normal < 81).astype(int)
    per["monsoon_share"] = per.jjas_mm / per.annual_mm
    per.to_parquet(OUT / "district_monsoon.parquet", index=False)

    cols = ["jjas_mm", "annual_mm", "rainy_days", "heavy_days", "very_heavy_days", "extreme_days",
            "longest_dry", "deficient", "monsoon_share"]
    nat = pd.DataFrame({c: wmean(per, ["year"], c, w) for c in cols}).reset_index()
    nat.rename(columns={"deficient": "share_area_deficient"}).to_csv(OUT / "monsoon_national_annual.csv", index=False)
    rows = []
    for c in cols:
        for (a, b), label in (((1901, 2025), "1901-2025"), ((1951, 2025), "1951-2025")):
            s = nat[nat.year.between(a, b)]
            rows.append({"variable": c, "period": label, **trend(s.year, s[c])})
    tr = pd.DataFrame(rows)
    tr.to_csv(OUT / "monsoon_national_trends.csv", index=False)
    dec = nat.assign(decade=(nat.year // 10) * 10).groupby("decade")[cols].mean().reset_index()
    dec.to_csv(OUT / "monsoon_by_decade.csv", index=False)

    dt = []
    for did, gg in per.groupby("district_id"):
        r = {"district_id": did}
        for c in ("jjas_mm", "heavy_days", "longest_dry", "rainy_days"):
            t = trend(gg[gg.year >= 1951].year, gg[gg.year >= 1951][c])
            r[f"{c}_per_decade"], r[f"{c}_mk_p"] = t["sen_per_decade"], t["mk_p"]
        dt.append(r)
    pd.DataFrame(dt).to_parquet(OUT / "district_monsoon_trends.parquet", index=False)
    print(tr[tr.period == "1951-2025"][["variable", "sen_per_decade", "mk_p"]].round(4).to_string(index=False))
    print(dec[["decade", "jjas_mm", "heavy_days", "longest_dry", "deficient"]].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
