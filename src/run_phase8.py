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
from src.models import (FEATURES, FEATURES_V2, PARSIMONIOUS, attribution_model, evaluate, evaluate_classifiers,
                        fit_attribution, fit_classifiers, fit_models, predict, prepare, scenario_features,
                        scenario_yields, transform_rain)

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
    rows = [_fe_row(name, smf.ols(FORMULA.format(heat=heat), data=d).fit(), d, heat) for name, d in variants.items()]
    w_ = base.assign(w=base.area_ha)
    rows.append(_fe_row("area-weighted (WLS)", smf.wls(FORMULA.format(heat=heat), data=w_, weights=w_.w).fit(), w_, heat))
    return pd.DataFrame(rows)


FORMULA = "yield_rel_anom ~ {heat} + np.log1p(rain_total) + C(unit_id) + C(year)"


def _fe_row(name: str, fit, d: pd.DataFrame, heat: str) -> dict:
    """One robustness row with 95% CIs under three error-clustering choices (D23).

    Errors are correlated across neighbouring districts (shared weather: 64 districts share one 1 deg
    temperature cell) and across districts in the same year. Clustering by district alone ignores both,
    so we also cluster by state, two-way by district + year, and two-way by state + year (spatial correlation
    within a state AND every district sharing the year). ci_low / ci_high = the widest of the four, so every
    number downstream uses the most conservative interval.
    """
    unit, state, yr = pd.factorize(d.unit_id)[0], pd.factorize(d.state_id)[0], pd.factorize(d.year)[0]
    groups = {"district": unit, "state": state,
              "district+year": np.column_stack([unit, yr]), "state+year": np.column_stack([state, yr])}
    i = fit.model.exog_names.index(heat)
    row = {"variant": name, "n": int(fit.nobs), "effect per +1C night temp": fit.params[heat]}
    for k, g in groups.items():
        r = fit.get_robustcov_results(cov_type="cluster", groups=g)
        lo, hi = r.conf_int()[i]
        row[f"ci_low_{k}"], row[f"ci_high_{k}"], row[f"p_{k}"] = lo, hi, r.pvalues[i]
    width = {k: row[f"ci_high_{k}"] - row[f"ci_low_{k}"] for k in groups}
    widest = max((k for k in groups if np.isfinite(width[k])), key=width.get)   # skip a failed (NaN) covariance
    row.update({"ci_low": row[f"ci_low_{widest}"], "ci_high": row[f"ci_high_{widest}"], "p": row[f"p_{widest}"],
                "ci_used": widest})
    return row


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

        # warming scenarios (D23): attribution model with district + year fixed effects.
        # Main = two-way FE Ridge on the full feature set. The other specifications are kept as a
        # check: if they disagree a lot with the main one, the headline number is fragile.
        attr = fit_attribution(m, feats)
        pm = prepare(crop, PARSIMONIOUS[crop], log_rain=log_rain)
        attr_small = fit_attribution(pm, PARSIMONIOUS[crop])
        specs = {
            "MAIN: two-way FE Ridge (full features)": (attribution_model(attr, "Two-way FE Ridge"), m, feats),
            "two-way FE OLS (full features)": (attribution_model(attr, "Two-way FE OLS"), m, feats),
            "two-way FE OLS (tmin, EDD, rain only)": (attribution_model(attr_small, "Two-way FE OLS"), pm, PARSIMONIOUS[crop]),
            "old: within OLS, no year FE (train years)": (mods["FE regression (OLS, within)"], m, feats),
        }
        scen, comp = [], []
        for dc in (1.0, 2.0):
            fs_raw = scenario_features("Wheat" if crop == "Wheat" else "Rice", dc, daily)
            for name, (model, mm, ff) in specs.items():
                fs = transform_rain(fs_raw, ff) if log_rain else fs_raw
                s = scenario_yields(model, mm, ff, fs).assign(delta_c=dc)
                s = s[(s.year >= 2018) & s.delta_rel_yield.notna()]          # recent climate (2018-22 seasons)
                comp.append({"spec": name, "delta_c": dc,
                             "area_weighted_change_pct": 100 * np.average(s.delta_rel_yield, weights=s.area_ha)})
                if name.startswith("MAIN"):
                    scen.append(s)
        pd.concat(scen).to_parquet(OUT / f"scenarios_{key}.parquet", index=False)
        comp = pd.DataFrame(comp).pivot(index="spec", columns="delta_c", values="area_weighted_change_pct")
        comp.columns = [f"+{c:g}C (%)" for c in comp.columns]
        comp.to_csv(OUT / f"scenario_model_comparison_{key}.csv")
        print(comp.round(2).to_string())
        summary[crop] = {"features": feats, "log_rain": log_rain,
                         "best_params": {k: v.best_params_ for k, v in mods.items() if hasattr(v, "best_params_")},
                         "ridge_alpha": float(mods["Ridge"][-1].alpha_),
                         "attribution_ridge_alpha": float(attr["Two-way FE Ridge"][-1].alpha_)}
        print(f"{crop}: done")
        print(ev_test.round(4).to_string())
    json.dump(summary, open(OUT / "run_summary.json", "w"), indent=2, default=str)


if __name__ == "__main__":
    np.random.seed(SEED)
    main()
