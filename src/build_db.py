"""Phase 9: build app/atlas.sqlite (+ app/districts.geojson) for the Crop-Climate Risk Atlas.

Tables
  districts    unit_id, d_name, state_id, zone, risk_prob_high, risk_label_source, + profile columns
  yields       unit_id, crop, year, area_ha, yield_t_ha, trend_full, yield_rel_anom, irr_share
  climate      unit_id, crop, year, season weather features (tmax_mean, tmin_mean, gdd, edd, rain_total, ...)
  sensitivity  unit_id, crop, heat_effect_per_c  (district FE-model change in yield per +1 C, from the grid)
  scenarios    unit_id, crop, delta_c (0.5..3.0), delta_rel_yield  (mean over 2018-22 seasons, two-way FE Ridge, D23)
  scenario_ci  crop, delta_c, group, estimate, lo, hi, ci_used, ...   (bootstrap intervals, D23)
  robustness   crop, variant, effect per +1C night temp, ci_low, ci_high, ...   (night-temperature FE regression)
  forecasts    unit_id, crop, year, actual, trend_train, pred_ridge   (test years 2018-22)
  meta         key, value   (sources, caveats, build date)
Everything is precomputed, so the app only reads.
"""
import datetime as dt
import json
import sqlite3

import numpy as np
import pandas as pd
from src.boundaries import load_pc11_districts
from src.config import PROCESSED, ROOT
from src.features import load_daily
from src.models import (FEATURES, FEATURES_V2, attribution_model, design, fit_attribution, prepare, scenario_features,
                        transform_rain)

APP = ROOT / "app"
DB = APP / "atlas.sqlite"
GRID = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
CHOICE = {"Wheat": (FEATURES_V2["Wheat"], True, "wheat"), "Rice (monsoon)": (FEATURES["Rice"], False, "rice_monsoon")}


def scenario_grid(daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for crop, (feats, log_rain, key) in CHOICE.items():
        m = prepare(crop, feats, log_rain=log_rain)
        fe = attribution_model(fit_attribution(m, feats))       # same model as run_phase8 (D23)
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
                   "linear model with district and year fixed effects, extrapolation beyond observed weather. Weather explains only 1-2% of "
                   "out-of-sample yield variation; forecasts are weak. Temperature grid is 1 deg (64 districts share one cell).",
    }
    with sqlite3.connect(DB) as con:
        for name, df in (("districts", districts), ("yields", yields), ("climate", climate), ("sensitivity", sens),
                         ("scenarios", scen), ("forecasts", fc), ("meta", pd.DataFrame(meta.items(), columns=["key", "value"]))):
            df.to_sql(name, con, if_exists="replace", index=False)
        # Phase 10 long-run climate tables (written only if `src.climate_trends` etc. have been run)
        CL = PROCESSED / "climate"
        extra = {"clim_annual": "national_annual.csv", "clim_trends": "national_trends.csv",
                 "clim_winters": "national_winters.csv", "clim_hot_days": "national_hot_days.csv",
                 "clim_records": "record_hot_years.csv", "monsoon_annual": "monsoon_national_annual.csv",
                 "monsoon_trends": "monsoon_national_trends.csv", "harvest_link": "harvest_link_summary.csv",
                 "clim_district_winters": "district_winter_change.csv", "clim_states": "state_climate_summary.csv"}
        for name, f in extra.items():
            if (CL / f).exists():
                pd.read_csv(CL / f).rename(columns={"district_id": "unit_id"}).to_sql(name, con, if_exists="replace",
                                                                                       index=False)
        if (CL / "district_trends.parquet").exists():
            dtr = pd.read_parquet(CL / "district_trends.parquet")
            dtr[dtr.period == "annual"].drop(columns="period").rename(columns={"district_id": "unit_id"}).to_sql(
                "clim_district_trends", con, if_exists="replace", index=False)
        # loss-year patterns (written only if `src.loss_patterns` has been run)
        PT = PROCESSED / "patterns"
        if (PT / "loss_by_year_wheat.csv").exists():
            by_year, reg_year, wx, bins = [], [], [], []
            for crop, key in (("Wheat", "wheat"), ("Rice (monsoon)", "rice_monsoon")):
                by_year.append(pd.read_csv(PT / f"loss_by_year_{key}.csv").assign(crop=crop))
                ry = pd.read_csv(PT / f"loss_region_year_{key}.csv").melt(id_vars="region", var_name="year", value_name="share_area_in_loss")
                reg_year.append(ry.assign(year=ry.year.astype(int), crop=crop))
                c = pd.read_csv(PT / f"loss_weather_by_region_{key}.csv").set_index(["region", "loss"])
                d = (c.xs(1, level="loss") - c.xs(0, level="loss")).reset_index().melt(id_vars="region", var_name="variable", value_name="z_loss_minus_normal")
                wx.append(d.assign(variable=d.variable.str.removeprefix("z_"), crop=crop))
                b = pd.read_csv(PT / f"loss_rate_by_weather_bin_{key}.csv").melt(id_vars=["region", "variable"], var_name="bin", value_name="loss_rate")
                bins.append(b.assign(crop=crop))
            for name, parts in (("loss_by_year", by_year), ("loss_region_year", reg_year), ("loss_weather", wx), ("loss_bins", bins)):
                df = pd.concat(parts, ignore_index=True)
                df[df.region != "Other"].to_sql(name, con, if_exists="replace", index=False) if "region" in df else df.to_sql(name, con, if_exists="replace", index=False)
        # D23: intervals and the night-temperature effect, so the app reads numbers instead of hard-coding them
        P8 = PROCESSED / "phase8"
        if (P8 / "scenario_ci.csv").exists():
            pd.read_csv(P8 / "scenario_ci.csv").to_sql("scenario_ci", con, if_exists="replace", index=False)
        rob = [pd.read_csv(P8 / f"robustness_{key}.csv").assign(crop=crop)
               for crop, (_, _, key) in CHOICE.items() if (P8 / f"robustness_{key}.csv").exists()]
        if rob:
            pd.concat(rob).to_sql("robustness", con, if_exists="replace", index=False)
        # D25: production, value and food equivalent, 2022-23, checked against official totals
        PV = PROCESSED / "value"
        for name, f in (("value_state_check", "state_check_2022.csv"), ("value_district", "district_value_2022.csv"),
                        ("value_india", "india_value_2022.csv"), ("value_series", "all_india_series.csv")):
            if (PV / f).exists():
                pd.read_csv(PV / f).to_sql(name, con, if_exists="replace", index=False)
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
