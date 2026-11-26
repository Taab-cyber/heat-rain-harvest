"""Phase 8: leak-free prediction of district yields (train <= 2017, test 2018-2022).

Everything data-dependent is fitted on training years only (DECISIONS D18):
  * yield trend per district (detrend_train_only)           -> target = relative anomaly vs that trend
  * district means used to make "within-district" features  -> training-year means only
  * irrigation: the district's TRAINING-period mean share (static). The same-year LUS value is
    not known before harvest, so using it would leak future information into a forecast.
  * hyper-parameters chosen by GroupKFold over training YEARS (whole years held out together)

Prediction in yield units:  yield_hat = trend_train * (1 + anomaly_hat)
Baseline ("trend only"):    yield_hat = trend_train            (i.e. anomaly_hat = 0)
Skill vs baseline:          1 - MSE(model) / MSE(baseline)     (> 0 means the model helps)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression, Ridge, RidgeCV
from sklearn.metrics import average_precision_score, balanced_accuracy_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import GridSearchCV, GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.config import PROCESSED, SEED, TRAIN_LAST_YEAR
from src.features import detrend_train_only

FEATURES = {          # version 1 (first run, D18)
    "Wheat": ["tmax_mean", "tmin_mean", "gdd", "edd", "mar_tmax_mean", "mar_hot_days_35", "edd_mar",
              "rain_total", "rain_nov_jan", "rainy_days", "rain_cv_monthly"],
    "Rice": ["tmax_mean", "tmin_mean", "gdd", "edd", "hot_days_35", "rain_total", "rain_jun_sep",
             "rainy_days", "rain_cv_monthly", "longest_dry_spell"],
}
FEATURES_V2 = {       # version 2 after the feature-engineering iteration (D19)
    "Wheat": FEATURES["Wheat"] + ["feb_tmax_mean", "edd30_feb_mar", "prev_monsoon_rain"],
    "Rice (monsoon)": ["tmax_mean", "tmin_mean", "gdd", "edd", "hot_days_35", "rain_jun", "rain_jul",
                       "rain_aug", "rain_sep", "rainy_days", "longest_dry_spell"],
}
# rain-type features are compared as log ratios to the district's normal (% of normal), not mm (D19)
RAIN_LIKE = ("rain_", "prev_monsoon_rain")


# ------------------------------------------------------------------ data preparation
def table_name(crop: str) -> str:
    return {"Rice (monsoon)": "rice_monsoon"}.get(crop, crop.lower())


def transform_rain(df: pd.DataFrame, feats: list[str]) -> pd.DataFrame:
    """log(1 + mm) for rain-type features, so deviations become ~ % of normal (D19)."""
    df = df.copy()
    for f in feats:
        if f.startswith(RAIN_LIKE) and f != "rain_cv_monthly":
            df[f] = np.log1p(df[f])
    return df


def prepare(crop: str, features: list[str] | None = None, model_table: pd.DataFrame | None = None,
            log_rain: bool = False) -> pd.DataFrame:
    """Analysis-sample rows with train-only trend, target and leak-free within-district features."""
    feats = features or FEATURES[crop]
    m = model_table if model_table is not None else pd.read_parquet(PROCESSED / f"model_{table_name(crop)}.parquet")
    if log_rain:
        m = transform_rain(m, feats)
    m = detrend_train_only(m[m.in_sample].copy())
    m = m.dropna(subset=feats + ["trend_train"]).copy()
    m = m[m.trend_train > 0]
    m["train"] = m.year <= TRAIN_LAST_YEAR
    means = m[m.train].groupby("unit_id")[feats].mean()            # training-year district means
    m = m[m.unit_id.isin(means.index)]                              # districts seen in training only
    dev = m[feats] - means.reindex(m.unit_id).to_numpy()
    for f in feats:
        m[f"d_{f}"] = dev[f].to_numpy()                             # within-district deviation
    irr = m[m.train].groupby("unit_id").irr_share.mean()
    m["irr_static"] = m.unit_id.map(irr).fillna(irr.median())       # known before the season
    m["target"] = m.yield_rel_anom_train
    m["loss_train"] = (m.target < -0.10).astype(int)
    return m


def design(m: pd.DataFrame, feats: list[str], with_irr_interactions: bool = True) -> pd.DataFrame:
    X = m[[f"d_{f}" for f in feats]].copy()
    X["irr_static"] = m.irr_static
    if with_irr_interactions:                                       # does irrigation change weather effects?
        for f in feats:
            X[f"d_{f}_x_irr"] = m[f"d_{f}"] * m.irr_static
    return X


# ------------------------------------------------------------------ models
def year_cv(train: pd.DataFrame, n_splits: int = 5):
    return list(GroupKFold(n_splits=n_splits).split(train, groups=train.year))


def fit_models(m: pd.DataFrame, feats: list[str]) -> dict:
    tr = m[m.train & m.target.notna()]
    Xtr, ytr = design(tr, feats), tr.target
    cv = year_cv(tr)
    models = {
        "FE regression (OLS, within)": LinearRegression().fit(Xtr, ytr),
        "Ridge": make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 4, 40), cv=cv)).fit(Xtr, ytr),
        "Random forest": GridSearchCV(
            RandomForestRegressor(n_estimators=400, n_jobs=-1, random_state=SEED),
            {"min_samples_leaf": [20, 50, 100], "max_features": [0.3, 0.6]},
            cv=cv, scoring="neg_mean_squared_error").fit(Xtr, ytr),
        "Gradient boosting": GridSearchCV(
            HistGradientBoostingRegressor(random_state=SEED, max_iter=300, early_stopping=False),
            {"learning_rate": [0.03, 0.1], "max_depth": [2, 3], "min_samples_leaf": [50, 100]},
            cv=cv, scoring="neg_mean_squared_error").fit(Xtr, ytr),
    }
    return models


def predict(models: dict, m: pd.DataFrame, feats: list[str]) -> pd.DataFrame:
    out = m[["unit_id", "year", "d_name", "state_id", "area_ha", "yield_t_ha", "trend_train", "target", "train"]].copy()
    out["pred_Baseline (trend only)"] = out.trend_train
    X = design(m, feats)
    for name, mod in models.items():
        out[f"pred_{name}"] = m.trend_train * (1 + mod.predict(X))
    return out


def evaluate(pred: pd.DataFrame, subset: str = "test") -> pd.DataFrame:
    d = pred[~pred.train] if subset == "test" else pred[pred.train]
    d = d.dropna(subset=["yield_t_ha"])
    base = ((d["pred_Baseline (trend only)"] - d.yield_t_ha) ** 2).mean()
    rows = []
    for c in [c for c in d.columns if c.startswith("pred_")]:
        err = d[c] - d.yield_t_ha
        rel_pred, rel_true = d[c] / d.trend_train - 1, d.yield_t_ha / d.trend_train - 1
        rows.append({"model": c[5:], "RMSE t/ha": np.sqrt((err ** 2).mean()), "MAE t/ha": err.abs().mean(),
                     "skill vs baseline": 1 - (err ** 2).mean() / base,
                     "corr(anomaly)": np.corrcoef(rel_pred, rel_true)[0, 1] if rel_pred.std() > 0 else np.nan})
    return pd.DataFrame(rows).set_index("model")


# ------------------------------------------------------------------ attribution model (D23)
# Forecasting and attribution are different questions:
#   * forecasting (fit_models above): only training years, no year effects, because a future year's
#     national shock is unknown when you forecast. Judged by out-of-sample skill.
#   * attribution (below): "how much does yield change when it is X degrees warmer, all else equal?"
#     Uses every in-sample year with district AND year fixed effects, so shocks that hit all of India
#     in one year (prices, policy, a national pest outbreak) cannot be credited to heat.
# In a warming scenario both fixed effects cancel (same district, same year, only the weather changes),
# so the scenario only needs the slope coefficients.
PARSIMONIOUS = {"Wheat": ["tmin_mean", "edd", "rain_total"], "Rice (monsoon)": ["tmin_mean", "edd", "rain_total"]}


def twoway_demean(X: pd.DataFrame, unit: np.ndarray, year: np.ndarray, tol: float = 1e-10,
                  max_iter: int = 500) -> pd.DataFrame:
    """Remove district and year means (two-way fixed effects) from every column.

    The panel is unbalanced, so one pass is not enough: alternate unit- and year-demeaning until
    nothing changes (method of alternating projections). The result equals the residual from
    regressing each column on district and year dummies (Frisch-Waugh-Lovell).
    """
    Z = X.to_numpy(dtype=float).copy()
    u = pd.factorize(unit)[0]
    y = pd.factorize(year)[0]
    nu, ny = u.max() + 1, y.max() + 1
    cu, cy = np.bincount(u, minlength=nu)[:, None], np.bincount(y, minlength=ny)[:, None]
    for _ in range(max_iter):
        mu = np.zeros((nu, Z.shape[1])); np.add.at(mu, u, Z); Z -= (mu / cu)[u]
        my = np.zeros((ny, Z.shape[1])); np.add.at(my, y, Z); Z -= (my / cy)[y]
        mu = np.zeros((nu, Z.shape[1])); np.add.at(mu, u, Z)
        if np.abs(mu / cu).max() < tol:
            break
    return pd.DataFrame(Z, index=X.index, columns=X.columns)


def attribution_rows(m: pd.DataFrame, feats: list[str]) -> pd.DataFrame:
    """In-sample rows (all years) with a target and every feature; target = anomaly vs full-period trend."""
    d = m.dropna(subset=feats + ["yield_rel_anom"]).copy()
    d["target_attr"] = d.yield_rel_anom            # descriptive trend is fine here: this is not a forecast
    return d


def fit_attribution(m: pd.DataFrame, feats: list[str], alpha: float | None = None,
                    unit: np.ndarray | None = None, year: np.ndarray | None = None) -> dict:
    """Two-way fixed-effects attribution models: OLS and Ridge on demeaned data.

    `unit`/`year` can be passed to override the group labels (the bootstrap uses relabelled copies).
    If `alpha` is given, Ridge uses it instead of choosing one by leave-years-out CV (faster for bootstrap).
    """
    d = attribution_rows(m, feats)
    unit = d.unit_id.to_numpy() if unit is None else unit
    year = d.year.to_numpy() if year is None else year
    X = design(d, feats).drop(columns=["irr_static"])             # constant within district -> removed by FE
    Xd = twoway_demean(X, unit, year)
    yd = twoway_demean(d[["target_attr"]], unit, year).target_attr
    ols = LinearRegression(fit_intercept=False).fit(Xd, yd)
    if alpha is None:
        ridge = make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 4, 40),
                                                        cv=GroupKFold(n_splits=5).split(Xd, groups=year)))
    else:
        ridge = make_pipeline(StandardScaler(), Ridge(alpha=alpha))
    ridge.fit(Xd, yd)
    return {"Two-way FE OLS": ols, "Two-way FE Ridge": ridge, "rows": d, "columns": list(X.columns)}


class _DropIrr:
    """Wrap an attribution model so it accepts design() output (which still has irr_static)."""
    def __init__(self, model):
        self.model = model

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return self.model.predict(X.drop(columns=["irr_static"], errors="ignore"))


def attribution_model(fitted: dict, name: str = "Two-way FE Ridge"):
    """A model usable by scenario_yields(): only differences of its predictions are meaningful."""
    return _DropIrr(fitted[name])


# ------------------------------------------------------------------ warming scenarios
def scenario_features(crop: str, delta_c: float, daily: pd.DataFrame | None = None) -> pd.DataFrame:
    """Season features recomputed after adding delta_c to every day's tmax and tmin.

    Uniform warming, rain unchanged, no adaptation (same sowing dates, varieties, irrigation).
    Recomputing from daily data means GDD, extreme degree days and hot-day counts respond
    non-linearly, as they would in reality, rather than by adding delta_c to averages.
    """
    from src.features import crop_features, load_daily
    d = (daily if daily is not None else load_daily()).copy()
    d["tmax"] = d["tmax"] + delta_c
    d["tmin"] = d["tmin"] + delta_c
    return crop_features(d, crop)


def scenario_yields(model, m: pd.DataFrame, feats: list[str], f_scen: pd.DataFrame) -> pd.DataFrame:
    """Predicted relative yield under the scenario minus under observed weather, same rows.

    The within-district deviations are taken against the SAME training-period means as the
    model, so a warmer climate shows up as larger deviations (what the model learned from).
    """
    base = m[["unit_id", "year"] + feats].copy()
    scen = base[["unit_id", "year"]].merge(f_scen[["unit_id", "year"] + feats], on=["unit_id", "year"], how="left")
    means = m[m.train].groupby("unit_id")[feats].mean()
    ms = m.copy()
    for f in feats:
        ms[f"d_{f}"] = (scen[f].to_numpy() - means.reindex(m.unit_id)[f].to_numpy())
    p_obs = model.predict(design(m, feats))
    p_scen = model.predict(design(ms, feats))
    out = m[["unit_id", "year", "d_name", "state_id", "area_ha", "irr_static"]].copy()
    out["delta_rel_yield"] = p_scen - p_obs          # change in yield as a fraction of trend yield
    return out


# ------------------------------------------------------------------ yield-loss classifier
def fit_classifiers(m: pd.DataFrame, feats: list[str]) -> dict:
    tr = m[m.train & m.target.notna()]
    Xtr, ytr = design(tr, feats), tr.loss_train
    cv = year_cv(tr)
    return {
        "Logistic (balanced)": make_pipeline(StandardScaler(), LogisticRegression(
            class_weight="balanced", C=0.1, max_iter=2000)).fit(Xtr, ytr),
        "Gradient boosting": GridSearchCV(
            HistGradientBoostingClassifier(random_state=SEED, max_iter=300, early_stopping=False, class_weight="balanced"),
            {"learning_rate": [0.03, 0.1], "max_depth": [2, 3]}, cv=cv, scoring="roc_auc").fit(Xtr, ytr),
    }


def evaluate_classifiers(clfs: dict, m: pd.DataFrame, feats: list[str]) -> pd.DataFrame:
    te = m[~m.train & m.target.notna()]
    y = te.loss_train
    clim = m[m.train].groupby("unit_id").loss_train.mean()             # district's historical loss frequency
    scores = {"Baseline (district loss frequency)": te.unit_id.map(clim).fillna(clim.mean())}
    for name, c in clfs.items():
        scores[name] = pd.Series(c.predict_proba(design(te, feats))[:, 1], index=te.index)
    rows = []
    for name, p in scores.items():
        rows.append({"model": name, "ROC-AUC": roc_auc_score(y, p), "PR-AUC": average_precision_score(y, p),
                     "Brier": brier_score_loss(y, p.clip(0, 1)),
                     "balanced acc (thr 0.5)": balanced_accuracy_score(y, p > 0.5) if name != "Baseline (district loss frequency)"
                     else balanced_accuracy_score(y, p > y.mean()),
                     "loss share in test": y.mean()})
    return pd.DataFrame(rows).set_index("model")
