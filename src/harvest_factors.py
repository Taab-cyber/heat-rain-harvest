"""Phase 10: harvest factors beyond weather (only those available from official sources without accounts).

Tested additions to the Phase 8 v2 weather features (DECISIONS D22):
  prev_yield_anom   last season's yield anomaly (% vs the train-only trend). Known before sowing, so it is
                    leak-free for a pre-harvest forecast. Captures persistence (soil moisture carry-over,
                    pests, input levels, reporting habits).
  tubewell_share    share of net irrigated area served by tubewells (DES Land Use Statistics), averaged over
                    training years only -> a static, pre-season district trait (groundwater dependence).
Protocol: same leak-free design as src.models (train <= 2017, training-year district means, static irrigation).
Model choice is made on 5-fold GroupKFold-by-year CV inside the training years; the 2018+ test set is then
scored once for the record. All variants use exactly the same rows, so differences come from the features.
Output: data/processed/climate/harvest_factors_<crop>.csv
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.config import PROCESSED, SEED
from src.features import detrend_train_only
from src.models import FEATURES_V2, design, prepare, table_name, year_cv

OUT = PROCESSED / "climate"


def add_factors(crop: str) -> pd.DataFrame:
    m = pd.read_parquet(PROCESSED / f"model_{table_name(crop)}.parquet")
    m = detrend_train_only(m[m.in_sample].copy()).sort_values(["unit_id", "year"])
    prev = m[["unit_id", "year", "yield_rel_anom_train"]].assign(year=lambda d: d.year + 1)
    m = m.drop(columns=["trend_train", "yield_anom_train", "yield_rel_anom_train"]).merge(
        prev.rename(columns={"yield_rel_anom_train": "prev_yield_anom"}), on=["unit_id", "year"], how="left")
    tw = (m.net_irr_tubewell_ha / m.net_irrigated_ha).where(m.net_irrigated_ha > 0)
    m["tubewell_share"] = m.unit_id.map(tw[m.year <= 2017].groupby(m.unit_id).mean())
    return m


def fit_eval(m: pd.DataFrame, feats: list[str], extra_static: list[str]) -> dict:
    X = design(m, feats)
    for c in extra_static:
        X[c] = m[c].to_numpy()
    tr, te = m.train.to_numpy(), ~m.train.to_numpy()
    y = m.target.to_numpy()
    cv = year_cv(m[tr])
    res = {}
    for name, mod in {
        "Ridge": make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 4, 40))),
        "Gradient boosting": HistGradientBoostingRegressor(random_state=SEED, max_iter=300, learning_rate=0.03,
                                                           max_depth=3, min_samples_leaf=100, early_stopping=False),
    }.items():
        p_cv = cross_val_predict(mod, X[tr], y[tr], cv=cv)
        mod.fit(X[tr], y[tr])
        p_te = mod.predict(X[te])
        base_tr, base_te = (y[tr] ** 2).mean(), (y[te] ** 2).mean()      # trend-only forecast = anomaly 0
        res[name] = {"cv_skill": 1 - ((p_cv - y[tr]) ** 2).mean() / base_tr,
                     "test_skill": 1 - ((p_te - y[te]) ** 2).mean() / base_te}
    return res


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for crop in FEATURES_V2:
        feats = FEATURES_V2[crop]
        base = add_factors(crop)
        m = prepare(crop, feats + ["prev_yield_anom"], model_table=base, log_rain=True)
        m = m[m.tubewell_share.notna()]
        rows = []
        for label, f, st in (("weather only (v2)", feats, []),
                             ("+ previous year's yield", feats + ["prev_yield_anom"], []),
                             ("+ tubewell share", feats, ["tubewell_share"]),
                             ("+ both", feats + ["prev_yield_anom"], ["tubewell_share"])):
            for model, r in fit_eval(m, f, st).items():
                rows.append({"crop": crop, "features": label, "model": model, **r})
        t = pd.DataFrame(rows)
        t.attrs["rows"] = len(m)
        t["rows_train"], t["rows_test"] = int(m.train.sum()), int((~m.train).sum())
        t.to_csv(OUT / f"harvest_factors_{table_name(crop)}.csv", index=False)
        print(crop, f"rows train {int(m.train.sum())}, test {int((~m.train).sum())}")
        print(t[["features", "model", "cv_skill", "test_skill"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
