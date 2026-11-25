"""Descriptive: which years and regions had yield losses, and what the weather looked like in those years.

Loss year = district yield more than 10% below its own long-run trend (D14; descriptive full-period trend).
Weather is compared WITHIN each district: z = (value - district mean) / district sd, so a "hot" year means hot
for that district. Regions group Census 2011 states. Outputs: data/processed/patterns/loss_*.csv
"""
import numpy as np
import pandas as pd

from src.config import PROCESSED

OUT = PROCESSED / "patterns"
REGION = {3: "North-west plains", 4: "North-west plains", 6: "North-west plains", 7: "North-west plains",
          1: "Himalayan", 2: "Himalayan", 5: "Himalayan",
          8: "West (dry)", 24: "West (dry)", 25: "West (dry)", 26: "West (dry)",
          9: "Gangetic plain", 10: "Gangetic plain", 19: "Gangetic plain",
          23: "Central", 22: "Central", 27: "Central",
          20: "East plateau and coast", 21: "East plateau and coast",
          28: "South", 29: "South", 30: "South", 32: "South", 33: "South", 34: "South",
          **{s: "North-east" for s in range(11, 19) if s != 16}, 16: "North-east"}
VARS = {"wheat": ["tmin_mean", "tmax_mean", "feb_tmax_mean", "mar_tmax_mean", "mar_hot_days_35", "rain_total",
                  "rain_nov_jan", "prev_monsoon_rain"],
        "rice_monsoon": ["rain_jun_sep", "longest_dry_spell", "rainy_days", "tmax_mean", "tmin_mean", "hot_days_35"]}


def load(key: str) -> pd.DataFrame:
    m = pd.read_parquet(PROCESSED / f"model_{key}.parquet")
    m = m[m.in_sample & m.yield_rel_anom.notna()].copy()
    m["region"] = m.state_id.map(REGION).fillna("Other")
    m["loss"] = (m.yield_rel_anom < -0.10).astype(int)
    for v in VARS[key]:
        g = m.groupby("unit_id")[v]
        m[f"z_{v}"] = (m[v] - g.transform("mean")) / g.transform("std")
    return m


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for key in VARS:
        m = load(key)
        w = m.area_ha
        yr = m.groupby("year").apply(lambda g: pd.Series({
            "share_area_in_loss": np.average(g.loss, weights=g.area_ha),
            "mean_anomaly_pct": np.average(g.yield_rel_anom, weights=g.area_ha) * 100,
            "districts": len(g)}), include_groups=False)
        yr.to_csv(OUT / f"loss_by_year_{key}.csv")
        ry = m.groupby(["region", "year"]).apply(lambda g: np.average(g.loss, weights=g.area_ha), include_groups=False).unstack()
        ry.to_csv(OUT / f"loss_region_year_{key}.csv")
        zc = [f"z_{v}" for v in VARS[key]]
        comp = m.groupby(["region", "loss"])[zc].mean().round(2)
        comp.to_csv(OUT / f"loss_weather_by_region_{key}.csv")
        # loss rate when the season is unusually cool / normal / hot (within-district tmin and key heat/rain var)
        rows = []
        for v in VARS[key][:3] if key == "rice_monsoon" else ["tmin_mean", "mar_tmax_mean", "rain_total"]:
            b = pd.cut(m[f"z_{v}"], [-np.inf, -1, 1, np.inf], labels=["low (z<-1)", "normal", "high (z>1)"])
            t = m.groupby(["region", b], observed=True).loss.mean().unstack().round(3)
            t["variable"] = v
            rows.append(t.reset_index())
        pd.concat(rows).to_csv(OUT / f"loss_rate_by_weather_bin_{key}.csv", index=False)

        print(f"\n===== {key}: {len(m):,} district-years, {m.unit_id.nunique()} districts, overall loss rate {m.loss.mean():.1%}")
        print("Worst years (share of crop area in loss):")
        print(yr.sort_values("share_area_in_loss", ascending=False).head(6).round(3).to_string())
        print("\nWorst 3 years per region (share of area in loss):")
        for r, s in ry.iterrows():
            top = s.dropna().sort_values(ascending=False).head(3)
            n = m[m.region == r].unit_id.nunique()
            print(f"  {r:24s} ({n:3d} districts, loss rate {m[m.region == r].loss.mean():.0%}): "
                  + ", ".join(f"{int(y)} ({v:.0%})" for y, v in top.items()))
        print("\nWeather in loss years minus normal years (within-district z, by region):")
        d = (comp.xs(1, level="loss") - comp.xs(0, level="loss")).round(2)
        d["n_loss"] = m[m.loss == 1].groupby("region").size()
        print(d.to_string())
        print("\nLoss rate by within-district weather bin:")
        print(pd.concat(rows).to_string(index=False))


if __name__ == "__main__":
    main()
