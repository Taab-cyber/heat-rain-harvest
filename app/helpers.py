"""Pure helper functions for the atlas (no Streamlit), so they can be unit-tested on small tables.

Tables follow app/atlas.sqlite (see src/build_db.py):
  districts    unit_id, d_name, state_id, ..., risk_prob_high, risk_label_source
  yields       unit_id, crop, year, area_ha, yield_t_ha, trend_full, yield_rel_anom, irr_share
  climate      unit_id, crop, year, season weather features
  sensitivity  unit_id, crop, heat_effect_per_c
  scenarios    unit_id, crop, delta_c, delta_rel_yield
"""
from __future__ import annotations

import numpy as np
import pandas as pd

BAD = -0.10                  # a bad year = yield more than 10% below the district's usual level (D14)
RISK_CUTS = (0.15, 0.30)     # share of bad years: below 15% low, 15-30% medium, 30% and above high
CROPS = ("Wheat", "Rice (monsoon)")


def season(year) -> str:
    """Agricultural year label: 2014 -> '2014-15'."""
    y = int(year)
    return f"{y}-{(y + 1) % 100:02d}"


def risk_level(share: float) -> str:
    """'low' / 'medium' / 'high' from the share of bad years; 'na' if unknown."""
    if share is None or pd.isna(share):
        return "na"
    if share < RISK_CUTS[0]:
        return "low"
    return "medium" if share < RISK_CUTS[1] else "high"


def risk_scores(yields: pd.DataFrame, districts: pd.DataFrame, crop: str, last_year: int = 2017) -> pd.DataFrame:
    """Share of bad years up to `last_year`, per district. For wheat, districts with too few observed years
    take the label-propagation probability (Phase 7) and are marked 'propagated'."""
    y = yields[(yields.crop == crop) & (yields.year <= last_year)].dropna(subset=["yield_rel_anom"])
    obs = y.groupby("unit_id").yield_rel_anom.apply(lambda s: (s < BAD).mean()).rename("risk_score")
    out = districts[["unit_id"]].drop_duplicates().set_index("unit_id").join(obs)
    out["risk_source"] = np.where(out.risk_score.notna(), "observed", None)
    if crop == "Wheat" and {"risk_prob_high", "risk_label_source"} <= set(districts.columns):
        d = districts.set_index("unit_id")
        prop = d.risk_prob_high.where(d.risk_label_source == "propagated").reindex(out.index)
        fill = out.risk_score.isna() & prop.notna()
        out.loc[fill, "risk_score"] = prop[fill]
        out.loc[fill, "risk_source"] = "propagated"
    return out.reset_index()


def district_summary(districts: pd.DataFrame, yields: pd.DataFrame, sensitivity: pd.DataFrame,
                     scenarios: pd.DataFrame, states: dict | None = None) -> pd.DataFrame:
    """One row per district and crop, for the CSV download."""
    states = states or {}
    rows = []
    for crop in CROPS:
        y = yields[yields.crop == crop]
        if y.empty:
            continue
        base = (y.groupby("unit_id").agg(mean_yield_t_ha=("yield_t_ha", "mean"), seasons=("yield_t_ha", "count"))
                .join(risk_scores(yields, districts, crop).set_index("unit_id")))
        s = sensitivity[sensitivity.crop == crop].set_index("unit_id").heat_effect_per_c
        base["heat_effect_pct_per_1C"] = s.reindex(base.index) * 100
        for dc in (1.0, 2.0):
            sc = scenarios[(scenarios.crop == crop) & (scenarios.delta_c == dc)].set_index("unit_id").delta_rel_yield
            base[f"change_pct_at_plus_{dc:g}C"] = sc.reindex(base.index) * 100
        base["risk_score_pct"] = base.pop("risk_score") * 100
        base["crop"] = crop
        rows.append(base.reset_index())
    out = pd.concat(rows, ignore_index=True)
    names = districts.drop_duplicates("unit_id").set_index("unit_id")
    out.insert(1, "district", out.unit_id.map(names.d_name))
    out.insert(2, "state", out.unit_id.map(names.state_id).map(states).fillna(out.unit_id.map(names.state_id).astype(str)))
    cols = ["unit_id", "district", "state", "crop", "seasons", "mean_yield_t_ha", "risk_score_pct", "risk_source",
            "heat_effect_pct_per_1C", "change_pct_at_plus_1C", "change_pct_at_plus_2C"]
    return out[cols].sort_values(["crop", "state", "district"]).round(3).reset_index(drop=True)


def district_panel(yields: pd.DataFrame, climate: pd.DataFrame, districts: pd.DataFrame, crop: str,
                   states: dict | None = None) -> pd.DataFrame:
    """District-year rows for one crop: yields plus that season's weather, for the CSV download."""
    states = states or {}
    y = yields[yields.crop == crop].drop(columns="crop")
    c = climate[climate.crop == crop].drop(columns="crop")
    p = y.merge(c, on=["unit_id", "year"], how="left")
    names = districts.drop_duplicates("unit_id").set_index("unit_id")
    p.insert(1, "district", p.unit_id.map(names.d_name))
    p.insert(2, "state", p.unit_id.map(names.state_id).map(states))
    p.insert(3, "season", p.year.map(season))
    p["bad_year"] = (p.yield_rel_anom < BAD).where(p.yield_rel_anom.notna())
    return p.sort_values(["state", "district", "year"]).round(4).reset_index(drop=True)


def drought_bad_years(district_yields: pd.DataFrame, district_climate: pd.DataFrame, z_cut: float = -0.8) -> int:
    """Number of bad years in one district that came with monsoon (Jun-Sep) rain well below its normal."""
    if "rain_jun_sep" not in district_climate or district_climate.rain_jun_sep.notna().sum() < 5:
        return 0
    r = district_climate.set_index("year").rain_jun_sep
    z = (r - r.mean()) / r.std()
    bad = district_yields.loc[district_yields.yield_rel_anom < BAD, "year"]
    return int((z.reindex(bad).fillna(0) < z_cut).sum())


def advice_keys(crop: str, bad_share: float, march_heat_pct: float | None, irr_share: float | None,
                drought_bad: int, max_items: int = 4) -> list[str]:
    """Which general actions to show for a district (keys of ADVICE in app.py), most relevant first.

    crop            'Wheat' or 'Rice (monsoon)'
    bad_share       share of seasons that were bad years
    march_heat_pct  district's percentile (0-1) of March days >= 35 C among wheat districts, or None
    irr_share       share of the crop area irrigated (0-1), or None
    drought_bad     bad years that came with a weak monsoon (drought_bad_years)
    """
    keys = []
    level = risk_level(bad_share)
    if crop == "Wheat" and level in ("medium", "high") and march_heat_pct is not None and march_heat_pct >= 2 / 3:
        keys.append("wheat_heat")
    if crop != "Wheat" and drought_bad >= 2:
        keys.append("rice_drought")
    if irr_share is not None and not pd.isna(irr_share) and irr_share < 0.5:
        keys.append("water")
    if level == "high" or "rice_drought" in keys:
        keys.append("insurance")
    keys.append("advisory")                              # always useful: local, current advice
    if len(keys) < 2:
        keys.append("insurance")
    seen = []
    for k in keys:
        if k not in seen:
            seen.append(k)
    return seen[:max_items]


def _shift_words(days: float, later: str, earlier: str) -> str:
    if pd.isna(days):
        return ""
    if abs(days) < 0.5:
        return "at about the same time"
    return f"about {abs(days):.0f} day{'s' if round(abs(days)) != 1 else ''} {later if days > 0 else earlier}"


def winter_sentence(name: str, then: float, now: float, start_shift: float, end_shift: float) -> str:
    """Plain-language winter change for one district (cool days per winter, 1952-81 vs 1996-2025)."""
    if pd.isna(then) or pd.isna(now):
        return f"No winter record for {name}."
    diff = now - then
    change = (f"{abs(diff):.0f} fewer" if diff <= -0.5 else f"{diff:.0f} more" if diff >= 0.5 else "about the same")
    text = (f"Cool days a winter in {name}: about **{then:.0f}** in 1952-81 and **{now:.0f}** in 1996-2025 "
            f"({change}).")
    start, end = _shift_words(start_shift, "later", "earlier"), _shift_words(end_shift, "later", "earlier")
    if start and end:
        text += f" Winter now starts {start} and ends {end}."
    return text


STATE_COLUMNS = {"state": "State", "districts": "Districts", "tmean_per_decade": "Warming, °C per decade",
                 "tmin_per_decade": "Nights, °C per decade", "tmax_per_decade": "Days, °C per decade",
                 "cool_days_then": "Cool days 1952-81", "cool_days_now": "Cool days 1996-2025",
                 "start_shift_days": "Winter start shift, days (+ = later)",
                 "end_shift_days": "Winter end shift, days (- = earlier)",
                 "wheat_yield_effect_pct": "Wheat already lost to warmer nights (%)"}


def state_table(states: pd.DataFrame, names: dict) -> pd.DataFrame:
    """State climate summary with readable names and columns, fastest-warming first."""
    s = states.assign(state=states.state_id.map(names).fillna("Other"))
    s = s.sort_values("tmean_per_decade", ascending=False)
    return s[list(STATE_COLUMNS)].rename(columns=STATE_COLUMNS).round(2).reset_index(drop=True)


def latin1(text: str) -> str:
    """Make text safe for the PDF's built-in Latin-1 fonts."""
    for a, b in (("−", "-"), ("–", "-"), ("—", "-"), ("≥", ">="), ("≤", "<="), ("’", "'"), ("‘", "'"),
                 ("“", '"'), ("”", '"'), ("…", "...")):
        text = text.replace(a, b)
    return text.encode("latin-1", "replace").decode("latin-1")
