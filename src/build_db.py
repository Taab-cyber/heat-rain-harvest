"""Phase 9: build app/atlas.sqlite (+ app/districts.geojson) for the Crop-Climate Risk Atlas.

Tables
  districts    unit_id, d_name, state_id, zone, risk_prob_high, risk_label_source, + profile columns
  yields       unit_id, crop, year, area_ha, yield_t_ha, trend_full, yield_rel_anom, irr_share
  climate      unit_id, crop, year, season weather features (tmax_mean, tmin_mean, gdd, edd, rain_total, ...)
  sensitivity  unit_id, crop, heat_effect_per_c  (district FE-model change in yield per +1 C, from the grid)
  scenarios    unit_id, crop, delta_c (0.5..3.0), delta_rel_yield  (mean over 2018-22 seasons, FE model, D18)
  forecasts    unit_id, crop, year, actual, trend_train, pred_ridge   (test years 2018-22)
  meta         key, value   (sources, caveats, build date)
Everything is precomputed, so the app only reads.
"""
import datetime as dt
import json
import sqlite3

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from src.boundaries import load_pc11_districts
from src.config import PROCESSED, ROOT
from src.features import load_daily
from src.models import FEATURES, FEATURES_V2, design, prepare, scenario_features, transform_rain

APP = ROOT / "app"
DB = APP / "atlas.sqlite"
GRID = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
CHOICE = {"Wheat": (FEATURES_V2["Wheat"], True, "wheat"), "Rice (monsoon)": (FEATURES["Rice"], False, "rice_monsoon")}


def scenario_grid(daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for crop, (feats, log_rain, key) in CHOICE.items():
        m = prepare(crop, feats, log_rain=log_rain)
        tr = m[m.train & m.target.notna()]
        fe = LinearRegression().fit(design(tr, feats), tr.target)
        recent = m[m.year >= 2018]
        base = fe.predict(design(recent, feats))
        means = m[m.train].groupby("unit_id")[feats].mean()
        for dc in GRID:
            fs = scenario_features("Wheat" if crop == "Wheat" else "Rice", dc, daily)
            fs = transform_rain(fs, feats) if log_rain else fs
            sc = recent[["unit_id", "year"]].merge(fs[["unit_id", "year"] + feats], on=["unit_id", "year"], how="left")
            ms = recent.copy()
            for f in feats:
                ms[f"d_{f}"] = sc[f].to_numpy() - means.reindex(recent.unit_id)[f].to_numpy()
            delta = fe.predict(design(ms, feats)) - base
            d = pd.DataFrame({"unit_id": recent.unit_id.to_numpy(), "delta": delta}).groupby("unit_id").delta.mean()
            rows.append(pd.DataFrame({"unit_id": d.index, "crop": crop, "delta_c": dc, "delta_rel_yield": d.values}))
        print(f"scenario grid {crop}: done")
    return pd.concat(rows, ignore_index=True)


def main() -> None:
    APP.mkdir(exist_ok=True)
    geo = load_pc11_districts()
    prof = pd.read_parquet(PROCESSED / "district_profiles.parquet")
    zones = pd.read_csv(PROCESSED / "risk_zones_wheat.csv", index_col=0)
    prop = pd.read_csv(PROCESSED / "risk_propagated_wheat.csv", index_col=0)
    districts = (geo[["district_id", "d_name", "state_id"]].rename(columns={"district_id": "unit_id"}).set_index("unit_id")
                 .join(prof.drop(columns=["d_name", "state_id"], errors="ignore")).join(zones).join(prop).reset_index())
    districts.loc[len(districts)] = {"unit_id": 9016, "d_name": "Tripura (all districts)", "state_id": 16}

    yields, climate = [], []
    for crop, key in (("Wheat", "wheat"), ("Rice (monsoon)", "rice_monsoon"), ("Rice", "rice")):
        m = pd.read_parquet(PROCESSED / f"model_{key}.parquet")
        m = m[m.in_sample]
        yields.append(m[["unit_id", "year", "area_ha", "yield_t_ha", "trend_full", "yield_rel_anom", "irr_share"]].assign(crop=crop))
        cols = [c for c in ["tmax_mean", "tmin_mean", "gdd", "edd", "rain_total", "mar_tmax_mean", "mar_hot_days_35",
                            "rain_jun_sep", "longest_dry_spell", "hot_days_35"] if c in m.columns]
        climate.append(m[["unit_id", "year"] + cols].assign(crop=crop))
    yields, climate = pd.concat(yields), pd.concat(climate)

    scen = scenario_grid(load_daily())
    sens = scen[scen.delta_c == 1.0].rename(columns={"delta_rel_yield": "heat_effect_per_c"})[["unit_id", "crop", "heat_effect_per_c"]]

    fc = []
    for crop, (_, _, key) in CHOICE.items():
        p = pd.read_parquet(PROCESSED / "phase8" / f"predictions_{key}.parquet")
        p = p[~p.train][["unit_id", "year", "yield_t_ha", "trend_train", "pred_Ridge"]]
        fc.append(p.rename(columns={"yield_t_ha": "actual", "pred_Ridge": "pred_ridge"}).assign(crop=crop))
    fc = pd.concat(fc)

    meta = {
        "built": dt.date.today().isoformat(),
        "sources": "Crop yields: DES Area-Production-Yield (data.desagri.gov.in). Irrigation: DES Land Use Statistics. "
                   "Weather: IMD gridded rainfall 0.25 deg (Pai et al. 2014) and temperature 1.0 deg. "
                   "Boundaries: Census 2011 district polygons, SHRUG Open Polygons v2.2 (Development Data Lab), also on AIKosh.",
        "caveats": "Districts are fixed Census 2011 units. Scenarios: uniform warming, rain unchanged, no adaptation; "
                   "linear fixed-effects model, extrapolation beyond observed weather. Weather explains only 1-2% of "
                   "out-of-sample yield variation; forecasts are weak. Temperature grid is 1 deg (64 districts share one cell).",
    }
    with sqlite3.connect(DB) as con:
        for name, df in (("districts", districts), ("yields", yields), ("climate", climate), ("sensitivity", sens),
                         ("scenarios", scen), ("forecasts", fc), ("meta", pd.DataFrame(meta.items(), columns=["key", "value"]))):
            df.to_sql(name, con, if_exists="replace", index=False)
        con.execute("CREATE INDEX IF NOT EXISTS ix_y ON yields(unit_id, crop)")
        con.execute("CREATE INDEX IF NOT EXISTS ix_c ON climate(unit_id, crop)")
        con.execute("CREATE INDEX IF NOT EXISTS ix_s ON scenarios(unit_id, crop)")

    g = geo.copy()
    g["geometry"] = g.geometry.simplify(0.01, preserve_topology=True)      # ~1 km tolerance: small file for the web map
    g.rename(columns={"district_id": "unit_id"})[["unit_id", "d_name", "geometry"]].to_file(APP / "districts.geojson", driver="GeoJSON")
    print(f"saved {DB} ({DB.stat().st_size/1e6:.1f} MB) and districts.geojson ({(APP/'districts.geojson').stat().st_size/1e6:.1f} MB)")
    with sqlite3.connect(DB) as con:
        for t in ("districts", "yields", "climate", "sensitivity", "scenarios", "forecasts"):
            print(t, con.execute(f"select count(*) from {t}").fetchone()[0])


if __name__ == "__main__":
    main()
