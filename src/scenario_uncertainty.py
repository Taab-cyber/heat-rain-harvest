"""Phase 8: cluster-bootstrap uncertainty for the warming scenarios (D18).

Resample whole DISTRICTS with replacement (B times), refit the FE regression on the
training years of the resample, and recompute the area-weighted mean yield change at
+1 / +2 C for the 2018-22 seasons, overall and by irrigation group. The 2.5th and 97.5th
percentiles give a 95% interval that includes uncertainty in the estimated coefficients.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from src.config import PROCESSED, SEED
from src.features import load_daily
from src.models import FEATURES, FEATURES_V2, design, prepare, scenario_features, transform_rain

OUT = PROCESSED / "phase8"
B = 300
CHOICE = {"Wheat": (FEATURES_V2["Wheat"], True), "Rice (monsoon)": (FEATURES["Rice"], False)}


def scen_design(m, feats, fs):
    scen = m[["unit_id", "year"]].merge(fs[["unit_id", "year"] + feats], on=["unit_id", "year"], how="left")
    means = m[m.train].groupby("unit_id")[feats].mean()
    ms = m.copy()
    for f in feats:
        ms[f"d_{f}"] = scen[f].to_numpy() - means.reindex(m.unit_id)[f].to_numpy()
    return design(ms, feats)


def main() -> None:
    rng = np.random.default_rng(SEED)
    daily = load_daily()
    rows = []
    for crop, (feats, log_rain) in CHOICE.items():
        m = prepare(crop, feats, log_rain=log_rain).reset_index(drop=True)
        X_obs = design(m, feats)
        X_s = {}
        for dc in (1.0, 2.0):
            fs = scenario_features("Wheat" if crop == "Wheat" else "Rice", dc, daily)
            X_s[dc] = scen_design(m, feats, transform_rain(fs, feats) if log_rain else fs)
        test = (m.year >= 2018).to_numpy() & X_s[2.0].notna().all(axis=1).to_numpy()
        irr_grp = pd.cut(m.irr_static, [0, .5, .9, 1.01], labels=["<50%", "50-90%", ">90%"]).astype(str).to_numpy()
        units = m.unit_id.unique()
        idx = {u: np.where(m.unit_id.to_numpy() == u)[0] for u in units}
        for b in range(B + 1):                                   # b = 0 is the original sample
            pick = units if b == 0 else rng.choice(units, size=len(units), replace=True)
            rr = np.concatenate([idx[u] for u in pick])
            tr = rr[m.train.to_numpy()[rr] & m.target.notna().to_numpy()[rr]]
            fe = LinearRegression().fit(X_obs.iloc[tr], m.target.iloc[tr])
            te = rr[test[rr]]
            w = m.area_ha.to_numpy()[te]
            for dc in (1.0, 2.0):
                delta = fe.predict(X_s[dc].iloc[te]) - fe.predict(X_obs.iloc[te])
                rec = {"crop": crop, "b": b, "delta_c": dc, "all": np.average(delta, weights=w)}
                for gname in ("<50%", "50-90%", ">90%"):
                    sel = irr_grp[te] == gname
                    rec[gname] = np.average(delta[sel], weights=w[sel]) if sel.any() else np.nan
                rows.append(rec)
        print(f"{crop}: done")
    R = pd.DataFrame(rows)
    R.to_parquet(OUT / "scenario_bootstrap.parquet", index=False)
    est = R[R.b == 0].set_index(["crop", "delta_c"])
    q = R[R.b > 0].groupby(["crop", "delta_c"]).quantile([0.025, 0.975]).unstack()
    for (crop, dc), r in est.iterrows():
        cols = ["all", "<50%", "50-90%", ">90%"]
        txt = "  ".join(f"{c}: {r[c]*100:+.1f}% [{q.loc[(crop, dc), (c, 0.025)]*100:+.1f}, {q.loc[(crop, dc), (c, 0.975)]*100:+.1f}]" for c in cols)
        print(f"{crop} +{dc:.0f}C  {txt}")


if __name__ == "__main__":
    main()
