"""Phase 8: bootstrap uncertainty for the warming scenarios (D18, revised in D23).

The scenario model is the two-way fixed-effects Ridge (district + year effects, D23). Its errors are
correlated in two ways that a district-only bootstrap ignores:
  * across space: neighbouring districts share weather (64 districts share one 1 deg temperature cell);
  * across time: every district in a year shares that year's national shock.
So we resample three ways and report all three:
  district : whole districts with replacement (the original D18 scheme)
  state    : whole states with replacement (keeps neighbouring districts together)
  year     : whole seasons with replacement (keeps each year's national shock together)
Each draw refits the model (Ridge alpha fixed at the value chosen on the full sample) and applies the new
coefficients to the SAME 2018-22 rows, so the interval measures coefficient uncertainty only.
Resampled clusters get fresh labels (a district drawn twice becomes two districts), as the fixed effects need.
The headline interval is the widest of the three schemes.

Outputs: data/processed/phase8/scenario_bootstrap.parquet, scenario_ci.csv
"""
import numpy as np
import pandas as pd

from src.config import PROCESSED, SEED
from src.features import load_daily
from src.models import (FEATURES, FEATURES_V2, attribution_model, attribution_rows, design, fit_attribution,
                        prepare, scenario_features, transform_rain)

OUT = PROCESSED / "phase8"
B = 300
CHOICE = {"Wheat": (FEATURES_V2["Wheat"], True), "Rice (monsoon)": (FEATURES["Rice"], False)}
SCHEMES = {"district": "unit_id", "state": "state_id", "year": "year"}
GROUPS = ("all", "<50%", "50-90%", ">90%")


def scen_design(m, feats, fs):
    scen = m[["unit_id", "year"]].merge(fs[["unit_id", "year"] + feats], on=["unit_id", "year"], how="left")
    means = m[m.train].groupby("unit_id")[feats].mean()
    ms = m.copy()
    for f in feats:
        ms[f"d_{f}"] = scen[f].to_numpy() - means.reindex(m.unit_id)[f].to_numpy()
    return design(ms, feats)


def resample(d: pd.DataFrame, col: str, rng) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Row positions of a cluster bootstrap draw, plus relabelled unit and year ids."""
    clusters = d[col].unique()
    pos = {c: np.where(d[col].to_numpy() == c)[0] for c in clusters}
    pick = rng.choice(clusters, size=len(clusters), replace=True)
    rows, unit, year = [], [], []
    for k, c in enumerate(pick):
        r = pos[c]
        rows.append(r)
        u, y = d.unit_id.to_numpy()[r].astype(str), d.year.to_numpy()[r].astype(str)
        if col == "year":
            y = np.char.add(y, f"_{k}")
        else:
            u = np.char.add(u, f"_{k}")
        unit.append(u), year.append(y)
    return np.concatenate(rows), np.concatenate(unit), np.concatenate(year)


def changes(model, X_obs, X_s, w, irr_grp) -> dict:
    out = {}
    for dc, Xs in X_s.items():
        delta = model.predict(Xs) - model.predict(X_obs)
        rec = {"all": np.average(delta, weights=w)}
        for g in GROUPS[1:]:
            sel = irr_grp == g
            rec[g] = np.average(delta[sel], weights=w[sel]) if sel.any() else np.nan
        out[dc] = rec
    return out


def main() -> None:
    rng = np.random.default_rng(SEED)
    daily = load_daily()
    rows = []
    for crop, (feats, log_rain) in CHOICE.items():
        m = prepare(crop, feats, log_rain=log_rain).reset_index(drop=True)
        d = attribution_rows(m, feats).reset_index(drop=True)
        main_fit = fit_attribution(d, feats)
        alpha = float(main_fit["Two-way FE Ridge"][-1].alpha_)

        # Build the scenario features on the FULL table: scen_design needs the training-year district means,
        # which a 2018+ subset does not contain (with only test rows every feature became NaN). Then keep 2018+.
        X_obs, X_s = design(m, feats), {}
        for dc in (1.0, 2.0):
            fs = scenario_features("Wheat" if crop == "Wheat" else "Rice", dc, daily)
            X_s[dc] = scen_design(m, feats, transform_rain(fs, feats) if log_rain else fs)
        ok = ((m.year >= 2018) & X_obs.notna().all(axis=1) & X_s[1.0].notna().all(axis=1)
              & X_s[2.0].notna().all(axis=1)).to_numpy()
        assert ok.sum() > 0, "no 2018+ rows with complete scenario features"
        test, X_obs = m[ok].reset_index(drop=True), X_obs[ok].reset_index(drop=True)
        X_s = {k: v[ok].reset_index(drop=True) for k, v in X_s.items()}
        w = test.area_ha.to_numpy()
        irr_grp = pd.cut(test.irr_static, [0, .5, .9, 1.01], labels=["<50%", "50-90%", ">90%"]).astype(str).to_numpy()

        est = changes(attribution_model(main_fit), X_obs, X_s, w, irr_grp)
        for dc, rec in est.items():
            rows.append({"crop": crop, "scheme": "estimate", "b": 0, "delta_c": dc, **rec})
        for scheme, col in SCHEMES.items():
            for b in range(1, B + 1):
                rr, unit, year = resample(d, col, rng)
                fit = fit_attribution(d.iloc[rr], feats, alpha=alpha, unit=unit, year=year)
                for dc, rec in changes(attribution_model(fit), X_obs, X_s, w, irr_grp).items():
                    rows.append({"crop": crop, "scheme": scheme, "b": b, "delta_c": dc, **rec})
            print(f"{crop}: {scheme} bootstrap done")
    R = pd.DataFrame(rows)
    R.to_parquet(OUT / "scenario_bootstrap.parquet", index=False)

    ci = []
    for (crop, dc), g in R.groupby(["crop", "delta_c"]):
        e = g[g.scheme == "estimate"].iloc[0]
        for grp in GROUPS:
            rec = {"crop": crop, "delta_c": dc, "group": grp, "estimate": e[grp]}
            for scheme in SCHEMES:
                q = g[g.scheme == scheme][grp].quantile([0.025, 0.975])
                rec[f"lo_{scheme}"], rec[f"hi_{scheme}"] = q.iloc[0], q.iloc[1]
            widest = max(SCHEMES, key=lambda s: rec[f"hi_{s}"] - rec[f"lo_{s}"])
            rec.update({"lo": rec[f"lo_{widest}"], "hi": rec[f"hi_{widest}"], "ci_used": widest})
            ci.append(rec)
    C = pd.DataFrame(ci)
    C.to_csv(OUT / "scenario_ci.csv", index=False)
    show = C[C.group == "all"].copy()
    for c in show.columns:
        if c.startswith(("estimate", "lo", "hi")):
            show[c] = (show[c] * 100).round(1)
    print(show.to_string(index=False))


if __name__ == "__main__":
    main()
