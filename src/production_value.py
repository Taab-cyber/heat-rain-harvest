"""Production in tonnes, value at MSP, margin over cost, and food equivalent, 2022-23 (D25).

Rule: a number is only produced where it can be checked against an official total.
  1. Sum our district production (DES APY portal, all seasons) by state for 2022-23 and compare with the
     official state production in Agricultural Statistics at a Glance 2024 (Tables 2.4(b), 2.5(b)).
     Major states are checked one by one; the remaining states are checked together against
     (official all-India - official major states).
  2. A state passes if our sum is within 5% of the official figure. Districts in a state that fails get no
     tonnes, rupees or people figures, only the reason. The official state and all-India totals are always shown.
  3. Value = production x MSP of the crop year (Table 2.71). Rice is converted to paddy with the out-turn
     ratio of 67 kg raw rice per 100 kg paddy (CAG Report 31 of 2015), because MSP is fixed for paddy.
  4. Margin = (MSP - projected cost A2+FL of the state, Table 2.73(a)) x quintals. Missing state cost -> no margin.
  5. Food equivalent = production / per-capita net availability (Table 3.6, 2022-23). It is an upper bound:
     gross production still includes seed, feed, waste, exports and stock changes.
Outputs: data/processed/value/*.csv
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import INTERIM, PROCESSED

OFFICIAL = INTERIM / "official"
OUT = PROCESSED / "value"
YEAR = 2022                     # agricultural year 2022-23, the last year in our crop data
TOL = 0.05                      # a state passes if our total is within 5% of the official total
CROPS = {"Wheat": "Wheat", "Rice": "Paddy (common)"}     # crop -> MSP row


def check_states(apy: pd.DataFrame, official: pd.DataFrame, year: int = YEAR, tol: float = TOL) -> pd.DataFrame:
    """Compare our state totals (tonnes) with official major-state totals (million tonnes); 'Other states' is
    the remainder of the official all-India figure. Returns one row per crop and state/group."""
    rows = []
    for crop in CROPS:
        ours = apy[(apy.crop == crop) & (apy.year == year)].groupby("state").production.sum() / 1e6
        off = official[official.crop == crop].set_index("state").prod_2022_mt
        majors = [s for s in off.index if s != "All India"]
        for s in majors:
            rows.append({"crop": crop, "state": s, "official_mt": off[s], "ours_mt": ours.get(s, 0.0)})
        rows.append({"crop": crop, "state": "Other states", "official_mt": off["All India"] - off[majors].sum(),
                     "ours_mt": ours.drop(majors, errors="ignore").sum()})
        rows.append({"crop": crop, "state": "All India", "official_mt": off["All India"], "ours_mt": ours.sum()})
    t = pd.DataFrame(rows)
    t["ratio"] = t.ours_mt / t.official_mt
    t["verified"] = (t.ratio - 1).abs() <= tol
    t["note"] = np.where(t.verified, "district figures add up to the official total (within 5%)",
                         "district figures do not add up to the official total: not shown")
    return t


def unit_states(district_map: pd.DataFrame) -> pd.Series:
    """Current state (as named in APY) of each Census 2011 district; a unit fed by two states gets 'mixed'."""
    m = district_map[(district_map.source == "apy") & district_map.pc11_district_code.notna()]
    s = m.groupby("pc11_district_code").state.agg(lambda x: x.iloc[0] if x.nunique() == 1 else "mixed")
    s.index = s.index.astype(int)
    return s


def district_values(panel: pd.DataFrame, states: pd.Series, check: pd.DataFrame, msp: pd.DataFrame,
                    cost: pd.DataFrame, avail: pd.DataFrame, out_turn: float, year: int = YEAR) -> pd.DataFrame:
    """One row per district and crop for `year`, with numbers only where the state passed the check."""
    p = panel[(panel.year == year) & panel.crop.isin(list(CROPS))]
    d = p.groupby(["unit_id", "crop"]).agg(production_t=("production", "sum"), area_ha=("area_ha", "sum")).reset_index()
    d["state"] = d.unit_id.map(states)
    ok = check.set_index(["crop", "state"]).verified
    major = set(check.state) - {"Other states", "All India"}
    grp = np.where(d.state.isin(major), d.state, "Other states")
    known = d.state.notna() & (d.state != "mixed")
    d["verified"] = [bool(ok.get((c, g), False)) and k for c, g, k in zip(d.crop, grp, known)]
    d["reason"] = np.where(d.verified, "",
                  np.where(d.state.isna(), "the district's state could not be identified",
                  np.where(d.state == "mixed", "district spans two states",
                           "this state's district figures do not add up to the official state total")))
    price = msp[msp.year == year].set_index("crop").msp_rs_q
    d["msp_rs_q"] = d.crop.map({c: price[m] for c, m in CROPS.items()})
    d["quintals_sold_basis"] = np.where(d.crop == "Rice", d.production_t / out_turn * 10, d.production_t * 10)
    cst = cost[cost.year == year].assign(crop=lambda x: x.crop.map({"Paddy": "Rice", "Wheat": "Wheat"}))
    d["cost_a2fl_rs_q"] = [cst.set_index(["crop", "state"]).cost_a2fl_rs_q.get((c, s), np.nan) for c, s in zip(d.crop, d.state)]
    d["value_rs"] = d.quintals_sold_basis * d.msp_rs_q
    d["margin_rs"] = d.quintals_sold_basis * (d.msp_rs_q - d.cost_a2fl_rs_q)
    d["margin_rs_per_acre"] = d.margin_rs / (d.area_ha * 2.4711)
    kg = avail.set_index("year").loc[year]
    d["people_equivalent"] = d.production_t * 1000 / np.where(d.crop == "Rice", kg.rice_kg, kg.wheat_kg)
    hide = ["production_t", "quintals_sold_basis", "value_rs", "margin_rs", "margin_rs_per_acre", "people_equivalent"]
    d.loc[~d.verified, hide] = np.nan
    return d


def india_values(official: pd.DataFrame, msp: pd.DataFrame, cost: pd.DataFrame, avail: pd.DataFrame,
                 out_turn: float, year: int = YEAR) -> pd.DataFrame:
    """All-India figures computed from official totals only (no district data involved)."""
    price = msp[msp.year == year].set_index("crop").msp_rs_q
    c = cost[(cost.year == year) & (cost.state == "All India")].set_index("crop").cost_a2fl_rs_q
    kg = avail.set_index("year").loc[year]
    rows = []
    for crop, mrow in CROPS.items():
        t = official[(official.crop == crop) & (official.state == "All India")].prod_2022_mt.iloc[0] * 1e6
        q = t / out_turn * 10 if crop == "Rice" else t * 10
        cc = c["Paddy" if crop == "Rice" else "Wheat"]
        rows.append({"crop": crop, "production_t": t, "quintals_sold_basis": q, "msp_rs_q": price[mrow],
                     "cost_a2fl_rs_q": cc, "value_rs": q * price[mrow], "margin_rs": q * (price[mrow] - cc),
                     "people_equivalent": t * 1000 / (kg.rice_kg if crop == "Rice" else kg.wheat_kg),
                     "availability_kg_per_person": kg.rice_kg if crop == "Rice" else kg.wheat_kg})
    return pd.DataFrame(rows)


def all_india_series(apy: pd.DataFrame, ai: pd.DataFrame) -> pd.DataFrame:
    """Our all-India sum vs the official all-India series, every year (shows when the gap opens)."""
    ours = apy[apy.crop.isin(list(CROPS))].groupby(["crop", "year"]).production.sum().div(1e6).rename("ours_mt")
    t = ai.set_index(["crop", "year"]).prod_mt.rename("official_mt").to_frame().join(ours, how="inner").reset_index()
    t["ratio"] = t.ours_mt / t.official_mt
    return t


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    official = pd.read_csv(OFFICIAL / "state_production.csv")
    ai = pd.read_csv(OFFICIAL / "all_india_production.csv")
    msp, cost = pd.read_csv(OFFICIAL / "msp.csv"), pd.read_csv(OFFICIAL / "cost_a2fl.csv")
    avail = pd.read_csv(OFFICIAL / "availability.csv")
    out_turn = float(pd.read_csv(OFFICIAL / "constants.csv").set_index("key").value["out_turn_raw_rice"])
    apy = pd.read_parquet(INTERIM / "apy_long.parquet")
    panel = pd.read_parquet(PROCESSED / "crop_panel_pc11.parquet")
    dmap = pd.read_csv(INTERIM / "district_map.csv")

    check = check_states(apy, official)
    series = all_india_series(apy, ai)
    dist = district_values(panel, unit_states(dmap), check, msp, cost, avail, out_turn)
    india = india_values(official, msp, cost, avail, out_turn)
    for name, df in (("state_check_2022", check), ("all_india_series", series), ("district_value_2022", dist),
                     ("india_value_2022", india)):
        df.to_csv(OUT / f"{name}.csv", index=False)
    print(check.round(3).to_string(index=False))
    print(series[series.year >= 2012].round(3).to_string(index=False))
    print(india.round(1).to_string(index=False))
    v = dist.groupby("crop").verified.agg(["sum", "size"])
    print("districts verified:", v.to_dict())


if __name__ == "__main__":
    main()
