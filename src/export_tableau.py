"""Phase 9: flat CSV exports for a Tableau Public dashboard (reports/tableau/). Build steps: TABLEAU.md.

Files
  district_year.csv     one row per district x year x crop: yield, trend, anomaly, loss flag, irrigation, key weather
  district_summary.csv  one row per district x crop: mean yield, risk score, heat sensitivity, +1/+2 C change, zone
  scenario_grid.csv     district x crop x warming (+0.5..+3 C): modelled yield change
  districts.geojson     Census 2011 district polygons (join field: unit_id)
"""
import shutil
import sqlite3

import pandas as pd

from src.config import ROOT

OUT = ROOT / "reports" / "tableau"
DB = ROOT / "app" / "atlas.sqlite"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB) as con:
        d = pd.read_sql("select * from districts", con)
        y = pd.read_sql("select * from yields", con)
        c = pd.read_sql("select * from climate", con)
        s = pd.read_sql("select * from scenarios", con)
        sens = pd.read_sql("select * from sensitivity", con)
    names = d[["unit_id", "d_name", "state_id"]]
    y = y[y.crop.isin(["Wheat", "Rice (monsoon)"])]
    dy = y.merge(c, on=["unit_id", "year", "crop"], how="left").merge(names, on="unit_id", how="left")
    dy["season"] = dy.year.astype(str) + "-" + (dy.year + 1 - 2000).astype(str).str.zfill(2)
    dy["loss_year"] = (dy.yield_rel_anom < -0.10).astype(int)
    dy["yield_anomaly_pct"] = dy.yield_rel_anom * 100
    dy.to_csv(OUT / "district_year.csv", index=False)

    risk = y[y.year <= 2017].groupby(["unit_id", "crop"]).yield_rel_anom.apply(lambda a: (a < -0.10).mean()).rename("risk_score")
    summ = (y.groupby(["unit_id", "crop"]).agg(mean_yield=("yield_t_ha", "mean"), mean_area_ha=("area_ha", "mean"),
                                               mean_irr_share=("irr_share", "mean")).join(risk).reset_index())
    for dc in (1.0, 2.0):
        summ = summ.merge(s[s.delta_c == dc][["unit_id", "crop", "delta_rel_yield"]].rename(
            columns={"delta_rel_yield": f"change_pct_{int(dc)}C"}), on=["unit_id", "crop"], how="left")
        summ[f"change_pct_{int(dc)}C"] *= 100
    summ = summ.merge(sens, on=["unit_id", "crop"], how="left").merge(d[["unit_id", "d_name", "state_id", "zone"]], on="unit_id", how="left")
    summ.to_csv(OUT / "district_summary.csv", index=False)
    s.assign(change_pct=s.delta_rel_yield * 100).merge(names, on="unit_id", how="left").to_csv(OUT / "scenario_grid.csv", index=False)
    shutil.copy(ROOT / "app" / "districts.geojson", OUT / "districts.geojson")
    for f in sorted(OUT.iterdir()):
        print(f.name, f"{f.stat().st_size/1e6:.2f} MB")


if __name__ == "__main__":
    main()
