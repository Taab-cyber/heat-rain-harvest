"""Phase 8 final run: models, classifiers, robustness, warming scenarios -> data/processed/phase8/.

Feature versions were chosen by leave-years-out CV on TRAINING years only (D19):
  Wheat          -> FEATURES_V2["Wheat"] with log rain
  Rice (monsoon) -> FEATURES["Rice"] (v1), mm rain
The 2018-2022 test years are evaluated once with these choices.
"""
import json

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from src.config import PROCESSED, SEED
from src.features import load_daily
from src.models import (FEATURES, FEATURES_V2, evaluate, evaluate_classifiers, fit_classifiers, fit_models,
                        predict, prepare, scenario_features, scenario_yields, transform_rain)

OUT = PROCESSED / "phase8"
OUT.mkdir(exist_ok=True)
CHOICE = {"Wheat": (FEATURES_V2["Wheat"], True), "Rice (monsoon)": (FEATURES["Rice"], False)}


def per_year(pred: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for yr, g in pred[~pred.train].groupby("year"):
        e = evaluate(g.assign(train=False))
        rows.append(e["skill vs baseline"].rename(yr))
    return pd.DataFrame(rows)


def robustness_fe(crop: str) -> pd.DataFrame:
    """Phase-6 style FE regression of the main heat effect under alternative samples (D11, D14, D15, D6c)."""
    m = pd.read_parquet(PROCESSED / f"model_{'wheat' if crop == 'Wheat' else 'rice_monsoon'}.parquet")
    heat = "tmin_mean"
    base = m[m.in_sample].dropna(subset=["yield_rel_anom", heat, "rain_total"])
    crop_panel = pd.read_parquet(PROCESSED / "crop_panel_pc11.parquet")
    c = crop_panel[crop_panel.crop == ("Wheat" if crop == "Wheat" else "Rice")]
    ratio = c.yield_raw / c.groupby(["unit_id", "crop", "season"]).yield_raw.transform("median")
    bad = {}
    for k in (2, 4):
        flag = (ratio > k) | (ratio < 1 / k)
        bad[k] = set(map(tuple, c.loc[flag, ["unit_id", "year"]].to_numpy()))
    variants = {
        "main (area >= 1000 ha, 3x flag)": base,
        "drop Madhya Pradesh 2018+ (D15)": base[~((base.state_id == 23) & (base.year >= 2018))],
        "drop districts with split parents (D6c)": base[~base.any_split_parent],
        "stricter flag 2x (D11)": base[[(u, y) not in bad[2] for u, y in zip(base.unit_id, base.year)]],
        "looser flag 4x (D11)": m[m.yield_t_ha.notna() & (m.area_ha >= 1000)].dropna(subset=["yield_rel_anom", heat, "rain_total"]).pipe(
            lambda d: d[[(u, y) not in bad[4] for u, y in zip(d.unit_id, d.year)]]),
        "area >= 5000 ha (D14)": base[base.area_ha >= 5000],
        "train years only (<= 2017)": base[base.year <= 2017],
    }
    rows = []
    for name, d in variants.items():
        f = smf.ols(f"yield_rel_anom ~ {heat} + np.log1p(rain_total) + C(unit_id) + C(year)", data=d).fit(
            cov_type="cluster", cov_kwds={"groups": d.unit_id})
        rows.append({"variant": name, "n": int(f.nobs), "effect per +1C night temp": f.params[heat],
                     "ci_low": f.conf_int().loc[heat, 0], "ci_high": f.conf_int().loc[heat, 1], "p": f.pvalues[heat]})
    w_ = base.assign(w=base.area_ha)
    f = smf.wls(f"yield_rel_anom ~ {heat} + np.log1p(rain_total) + C(unit_id) + C(year)", data=w_, weights=w_.w).fit(
        cov_type="cluster", cov_kwds={"groups": w_.unit_id})
    rows.append({"variant": "area-weighted (WLS)", "n": int(f.nobs), "effect per +1C night temp": f.params[heat],
                 "ci_low": f.conf_int().loc[heat, 0], "ci_high": f.conf_int().loc[heat, 1], "p": f.pvalues[heat]})
    return pd.DataFrame(rows)


def main() -> None:
    daily = load_daily()
    summary = {}
    for crop, (feats, log_rain) in CHOICE.items():
        key = "wheat" if crop == "Wheat" else "rice_monsoon"
        m = prepare(crop, feats, log_rain=log_rain)
        mods = fit_models(m, feats)
        pred = predict(mods, m, feats)
        pred.to_parquet(OUT / f"predictions_{key}.parquet", index=False)
        ev_test, ev_train = evaluate(pred, "test"), evaluate(pred, "train")
        ev_test.to_csv(OUT / f"eval_test_{key}.csv"); ev_train.to_csv(OUT / f"eval_train_{key}.csv")
        per_year(pred).to_csv(OUT / f"skill_by_year_{key}.csv")
        clfs = fit_classifiers(m, feats)
        evaluate_classifiers(clfs, m, feats).to_csv(OUT / f"eval_classifier_{key}.csv")
        robustness_fe(crop).to_csv(OUT / f"robustness_{key}.csv", index=False)

        # warming scenarios with the interpretable FE regression (linear in recomputed features)
        fe = mods["FE regression (OLS, within)"]
        scen = []
        for dc in (1.0, 2.0):
            fs = scenario_features("Wheat" if crop == "Wheat" else "Rice", dc, daily)
            if log_rain:
                fs = transform_rain(fs, feats)
            s = scenario_yields(fe, m, feats, fs).assign(delta_c=dc)
            scen.append(s[s.year >= 2018])                 # apply to the recent climate (2018-22 seasons)
        pd.concat(scen).to_parquet(OUT / f"scenarios_{key}.parquet", index=False)
        summary[crop] = {"features": feats, "log_rain": log_rain,
                         "best_params": {k: v.best_params_ for k, v in mods.items() if hasattr(v, "best_params_")},
                         "ridge_alpha": float(mods["Ridge"][-1].alpha_)}
        print(f"{crop}: done")
        print(ev_test.round(4).to_string())
    json.dump(summary, open(OUT / "run_summary.json", "w"), indent=2, default=str)


if __name__ == "__main__":
    np.random.seed(SEED)
    main()
