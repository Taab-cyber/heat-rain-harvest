"""D26: do suspected rice/paddy reporting switches change the results?

Step 1 (scan). For every state and crop, state yield = district production / district area (DES APY, all
seasons). A *step* in year t = median yield of years t..t+2 divided by median yield of years t-3..t-1. Weather
moves yields up or down for a single year; a reporting change moves the level and keeps it there. A step of
1.35 or more (or 1/1.35 or less) that is also >= 1.35 in the single year-on-year change is flagged. 1.35 is
well below the paddy/rice factor of 1/0.67 = 1.49 and well above normal year-to-year variation of state yields.
The last season (2022-23) has no later years, so for it the year-on-year change alone is used (>= 1.4).

Step 2 (re-estimate). Drop the flagged state-seasons for that crop (and, for a step, every later season of the
state, because the level never comes back), recompute each district's trend on the remaining years, and rerun:
  a) the night-temperature fixed-effects regression (main specification, four clustering choices);
  b) the warming scenarios with the attribution model (two-way fixed-effects Ridge, D23), point estimates.
Outputs: data/processed/phase8/unit_switch_scan.csv, unit_switch_results.csv
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from src.config import INTERIM, PROCESSED
from src.features import detrend_full, load_daily
from src.models import (FEATURES, FEATURES_V2, attribution_model, fit_attribution, prepare, scenario_features,
                        scenario_yields, transform_rain)
from src.run_phase8 import FORMULA, _fe_row

OUT = PROCESSED / "phase8"
STEP, YOY, LAST_YOY = 1.35, 1.35, 1.40
STATE_ID = {"Andhra Pradesh": 28, "Telangana": 28, "Bihar": 10, "Madhya Pradesh": 23, "Odisha": 21,
            "Chhattisgarh": 22, "Uttar Pradesh": 9, "West Bengal": 19, "Punjab": 3, "Haryana": 6, "Assam": 18,
            "Jharkhand": 20, "Karnataka": 29, "Tamil Nadu": 33, "Maharashtra": 27, "Gujarat": 24, "Rajasthan": 8,
            "Kerala": 32, "Uttarakhand": 5, "Himachal Pradesh": 2, "Jammu and Kashmir": 1, "Tripura": 16,
            "Manipur": 14, "Meghalaya": 17, "Nagaland": 13, "Mizoram": 15, "Arunachal Pradesh": 12, "Sikkim": 11,
            "Goa": 30, "Puducherry": 34}


def scan(apy: pd.DataFrame, min_area_ha: float = 1e5) -> pd.DataFrame:
    rows = []
    for (crop, state), g in apy[apy.crop.isin(["Wheat", "Rice"])].groupby(["crop", "state"]):
        s = g.groupby("year").agg(p=("production", "sum"), a=("area_ha", "sum"))
        s = s[s.a >= min_area_ha]                                  # ignore states where the crop is marginal
        y = (s.p / s.a).sort_index()
        years = list(y.index)
        for i, t in enumerate(years):
            if i == 0:
                continue
            yoy = y[t] / y[years[i - 1]]
            before = y[[v for v in years[max(0, i - 3):i]]].median()
            after = y[[v for v in years[i:i + 3]]].median()
            step = after / before
            last = i == len(years) - 1
            hit = (abs(np.log(yoy)) >= np.log(LAST_YOY)) if last else \
                  (abs(np.log(step)) >= np.log(STEP) and abs(np.log(yoy)) >= np.log(YOY) and np.sign(np.log(step)) == np.sign(np.log(yoy)))
            if hit:
                rows.append({"crop": crop, "state": state, "year": t, "yield_before": round(y[years[i - 1]]),
                             "yield_t": round(y[t]), "yoy": yoy, "step_3yr": step, "last_season": last})
    return pd.DataFrame(rows)


def redetrend(m: pd.DataFrame) -> pd.DataFrame:
    keep = ["trend_full", "yield_anom", "yield_rel_anom", "yield_loss"]
    m = m.drop(columns=[c for c in keep if c in m.columns])
    m = detrend_full(m.sort_values(["unit_id", "year"]).reset_index(drop=True))
    m["yield_loss"] = (m.yield_rel_anom < -0.10).where(m.yield_rel_anom.notna())
    return m


def night_effect(m: pd.DataFrame, label: str) -> dict:
    base = m[m.in_sample].dropna(subset=["yield_rel_anom", "tmin_mean", "rain_total"])
    r = _fe_row(label, smf.ols(FORMULA.format(heat="tmin_mean"), data=base).fit(), base, "tmin_mean")
    return {"n": r["n"], "night_effect_pct": r["effect per +1C night temp"] * 100, "ci_low_pct": r["ci_low"] * 100,
            "ci_high_pct": r["ci_high"] * 100, "p": r["p"], "ci_used": r["ci_used"]}


def scenarios(m: pd.DataFrame, crop: str, feats: list[str], log_rain: bool, daily) -> dict:
    mm = prepare(crop, feats, model_table=m, log_rain=log_rain)
    model = attribution_model(fit_attribution(mm, feats))
    out = {}
    for dc in (1.0, 2.0):
        fs = scenario_features("Wheat" if crop == "Wheat" else "Rice", dc, daily)
        fs = transform_rain(fs, feats) if log_rain else fs
        s = scenario_yields(model, mm, feats, fs)
        s = s[(s.year >= 2018) & s.delta_rel_yield.notna()]
        out[f"plus_{dc:g}C_pct"] = 100 * np.average(s.delta_rel_yield, weights=s.area_ha)
    return out


def irrigation_interaction(m: pd.DataFrame, label: str) -> dict:
    """Notebook 06, section 10 (rice): yield anomaly ~ monsoon deviation x irrigation + tmax + district + year FE,
    district-clustered errors, exactly as published. Returns the cost of a monsoon 20% below normal at 20% and
    95% irrigation, and the interaction p-value."""
    r = m[m.in_sample].copy()
    r["rain_dev_pct"] = r.rain_jun_sep / r.groupby("unit_id").rain_jun_sep.transform("mean") - 1
    dr = r.dropna(subset=["yield_rel_anom", "irr_share", "rain_dev_pct", "tmax_mean"]).copy()
    dr["irr_c"] = dr.irr_share - dr.irr_share.mean()
    fr = smf.ols("yield_rel_anom ~ rain_dev_pct * irr_c + tmax_mean + C(unit_id) + C(year)", data=dr).fit(
        cov_type="cluster", cov_kwds={"groups": dr.unit_id})
    eff = lambda irr: -0.2 * (fr.params["rain_dev_pct"] + fr.params["rain_dev_pct:irr_c"] * (irr - dr.irr_share.mean())) * 100
    return {"variant": label, "n": int(fr.nobs), "deficit20_at_20pct_irr": eff(0.2), "deficit20_at_95pct_irr": eff(0.95),
            "interaction": fr.params["rain_dev_pct:irr_c"], "interaction_p": fr.pvalues["rain_dev_pct:irr_c"]}


def irrigation_main() -> None:
    m = pd.read_parquet(PROCESSED / "model_rice.parquet")
    cases = {"drop Madhya Pradesh 2022-23": (m.state_id == 23) & (m.year == 2022),
             "drop Bihar before 2011-12": (m.state_id == 10) & (m.year <= 2010),
             "drop all of Odisha": m.state_id == 21}
    cases["drop all three"] = cases["drop Madhya Pradesh 2022-23"] | cases["drop Bihar before 2011-12"] | \
        cases["drop all of Odisha"]
    rows = [irrigation_interaction(m, "main (as published)")]
    for label, drop in cases.items():
        mv = m.copy()
        mv.loc[drop.to_numpy(), "in_sample"] = False
        rows.append(irrigation_interaction(redetrend(mv), label))
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "unit_switch_irrigation.csv", index=False)
    print(res.round(4).to_string(index=False))


def main() -> None:
    apy = pd.read_parquet(INTERIM / "apy_long.parquet")
    flags = scan(apy)
    flags.to_csv(OUT / "unit_switch_scan.csv", index=False)
    print(flags.round(2).to_string(index=False))

    # The scan alone cannot tell a reporting change from a drought and its recovery (most hits are the latter,
    # e.g. Chhattisgarh 2000-2003). Only cases with independent evidence (comparison with official 2022-23 state
    # figures, D25) are tested, separately and together.
    daily = load_daily()
    feats, log_rain = FEATURES["Rice"], False
    m = pd.read_parquet(PROCESSED / "model_rice_monsoon.parquet")
    cases = {
        "drop Madhya Pradesh 2022-23": (m.state_id == 23) & (m.year == 2022),
        "drop Bihar before 2011-12": (m.state_id == 10) & (m.year <= 2010),
        "drop all of Odisha": m.state_id == 21,
    }
    cases["drop all three"] = cases["drop Madhya Pradesh 2022-23"] | cases["drop Bihar before 2011-12"] | \
        cases["drop all of Odisha"]
    rows = []
    for label, drop in [("main (as published)", None)] + list(cases.items()):
        mv = m
        if drop is not None:
            mv = m.copy()
            mv.loc[drop.to_numpy(), "in_sample"] = False
            mv = redetrend(mv)
        rec = {"crop": "Rice (monsoon)", "variant": label,
               "rows_dropped": 0 if drop is None else int((drop & m.in_sample).sum())}
        rec.update(night_effect(mv, label))
        rec.update(scenarios(mv, "Rice (monsoon)", feats, log_rain, daily))
        rows.append(rec)
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in rec.items()})
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "unit_switch_results.csv", index=False)
    print(res.round(3).to_string(index=False))


if __name__ == "__main__":
    import sys
    irrigation_main() if "--irrigation" in sys.argv else main()
