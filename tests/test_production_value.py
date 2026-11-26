"""Tests for src/production_value.py on small synthetic tables (no data files needed)."""
import numpy as np
import pandas as pd
import pytest

from src.production_value import check_states, district_values, india_values


def _official():
    rows = []
    for crop in ("Wheat", "Rice"):
        rows += [{"crop": crop, "state": "Good", "prod_2022_mt": 1.0},
                 {"crop": crop, "state": "Bad", "prod_2022_mt": 1.0},
                 {"crop": crop, "state": "All India", "prod_2022_mt": 2.5}]   # 0.5 Mt in other states
    return pd.DataFrame(rows)


def _apy():
    rows = []
    for crop in ("Wheat", "Rice"):
        rows += [{"crop": crop, "year": 2022, "state": "Good", "production": 1.02e6},   # +2%: passes
                 {"crop": crop, "year": 2022, "state": "Bad", "production": 1.30e6},    # +30%: fails
                 {"crop": crop, "year": 2022, "state": "Small", "production": 0.49e6},  # other states -2%: passes
                 {"crop": crop, "year": 2021, "state": "Bad", "production": 9e9}]       # other years ignored
    return pd.DataFrame(rows)


def _inputs():
    msp = pd.DataFrame({"crop": ["Wheat", "Paddy (common)"], "year": [2022, 2022], "msp_rs_q": [2125.0, 2040.0]})
    cost = pd.DataFrame({"crop": ["Wheat", "Paddy", "Wheat", "Paddy"], "state": ["Good", "Good", "All India", "All India"],
                         "year": 2022, "cost_a2fl_rs_q": [1000.0, 1300.0, 1065.0, 1360.0]})
    avail = pd.DataFrame({"year": [2022], "rice_kg": [69.6], "wheat_kg": [68.8]})
    return msp, cost, avail


def test_check_states_flags_and_other_states_group():
    t = check_states(_apy(), _official()).set_index(["crop", "state"])
    assert bool(t.loc[("Wheat", "Good"), "verified"]) and not bool(t.loc[("Wheat", "Bad"), "verified"])
    assert t.loc[("Rice", "Other states"), "official_mt"] == pytest.approx(0.5)
    assert bool(t.loc[("Rice", "Other states"), "verified"])
    assert t.loc[("Wheat", "All India"), "ours_mt"] == pytest.approx(2.81)


def test_district_values_hide_unverified_and_convert_rice_to_paddy():
    check = check_states(_apy(), _official())
    panel = pd.DataFrame({"unit_id": [1, 2, 1, 3], "year": 2022, "crop": ["Wheat", "Wheat", "Rice", "Rice"],
                          "production": [1000.0, 1000.0, 670.0, 500.0], "area_ha": [250.0, 250.0, 100.0, 100.0]})
    states = pd.Series({1: "Good", 2: "Bad", 3: "Small"})
    msp, cost, avail = _inputs()
    d = district_values(panel, states, check, msp, cost, avail, 0.67).set_index(["unit_id", "crop"])
    w = d.loc[(1, "Wheat")]
    assert w.verified and w.value_rs == pytest.approx(1000 * 10 * 2125)              # 10 quintals per tonne
    assert w.margin_rs == pytest.approx(1000 * 10 * (2125 - 1000))
    assert w.margin_rs_per_acre == pytest.approx(w.margin_rs / (250 * 2.4711))
    assert w.people_equivalent == pytest.approx(1000 * 1000 / 68.8)
    r = d.loc[(1, "Rice")]
    assert r.quintals_sold_basis == pytest.approx(670 / 0.67 * 10)                    # 1000 t paddy
    assert r.value_rs == pytest.approx(10000 * 2040)
    bad = d.loc[(2, "Wheat")]
    assert not bad.verified and np.isnan(bad.production_t) and np.isnan(bad.value_rs) and "official" in bad.reason
    small = d.loc[(3, "Rice")]
    assert small.verified and np.isnan(small.margin_rs)                               # no state cost -> no margin


def test_district_with_unknown_state_is_never_shown():
    check = check_states(_apy(), _official())
    panel = pd.DataFrame({"unit_id": [9], "year": 2022, "crop": ["Wheat"], "production": [100.0], "area_ha": [10.0]})
    msp, cost, avail = _inputs()
    d = district_values(panel, pd.Series({1: "Good"}), check, msp, cost, avail, 0.67).iloc[0]
    assert not d.verified and np.isnan(d.value_rs) and "could not be identified" in d.reason


def test_india_values_use_official_totals_only():
    msp, cost, avail = _inputs()
    v = india_values(_official(), msp, cost, avail, 0.67).set_index("crop")
    assert v.loc["Wheat", "production_t"] == pytest.approx(2.5e6)
    assert v.loc["Rice", "quintals_sold_basis"] == pytest.approx(2.5e6 / 0.67 * 10)
    assert v.loc["Wheat", "margin_rs"] == pytest.approx(2.5e6 * 10 * (2125 - 1065))
