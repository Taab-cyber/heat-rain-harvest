"""Tests for the winter-change and state-summary tables (src/climate_summary.py) and their app wording
(app/helpers.py), on small synthetic tables. No data files needed.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.climate_summary import district_winter_change, state_summary

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from helpers import state_table, winter_sentence  # noqa: E402


def winters():
    """District 1: 90 cool days starting day 45, ending day 140, then 80 days starting 50, ending 136.
    District 2: no cool days at all in the recent period (first/last day missing)."""
    rows = []
    for s in range(1952, 2026):
        old = s <= 1981
        rows.append({"district_id": 1, "season": s, "cool_days": 90 if old else 80,
                     "first_cool_day": 45 if old else 50, "last_cool_day": 140 if old else 136})
        rows.append({"district_id": 2, "season": s, "cool_days": 30 if old else 0,
                     "first_cool_day": 60 if old else np.nan, "last_cool_day": 90 if old else np.nan})
    return pd.DataFrame(rows)


def test_winter_change_periods_and_signs():
    w = district_winter_change(winters()).set_index("district_id")
    assert w.loc[1, "cool_days_then"] == 90 and w.loc[1, "cool_days_now"] == 80
    assert w.loc[1, "cool_days_change"] == -10
    assert w.loc[1, "start_shift_days"] == 5          # starts later: positive
    assert w.loc[1, "end_shift_days"] == -4           # ends earlier: negative
    # 1982-1995 belongs to neither period, so changing it must change nothing
    per = winters()
    per.loc[per.season.between(1982, 1995), "cool_days"] = 999
    assert district_winter_change(per).set_index("district_id").loc[1, "cool_days_then"] == 90


def test_winter_change_no_recent_cool_days():
    w = district_winter_change(winters()).set_index("district_id")
    assert w.loc[2, "cool_days_now"] == 0
    assert np.isnan(w.loc[2, "start_shift_days"])     # no cool day, so no start date, not a fake 0


def test_state_summary_weights():
    trends = pd.DataFrame({"district_id": [1, 2, 3], "tmean_per_decade": [0.1, 0.3, 0.2],
                           "tmax_per_decade": [0.0, 0.0, 0.0], "tmin_per_decade": [0.2, 0.2, 0.2]})
    win = district_winter_change(winters())
    wheat = pd.DataFrame({"district_id": [1, 2], "warming_c": [1.0, 0.0],
                          "implied_yield_effect_pct": [-6.0, 0.0], "area_ha": [300.0, 100.0]})
    area = pd.Series([1.0, 3.0, 5.0], index=[1, 2, 3])
    state_of = pd.Series([10, 10, 20], index=[1, 2, 3])
    s = state_summary(trends, win, wheat, area, state_of).set_index("state_id")
    assert s.loc[10, "tmean_per_decade"] == pytest.approx((0.1 * 1 + 0.3 * 3) / 4)      # land-area weights
    assert s.loc[10, "wheat_yield_effect_pct"] == pytest.approx(-6.0 * 300 / 400)        # wheat-area weights
    assert np.isnan(s.loc[20, "wheat_yield_effect_pct"])                                 # no wheat: blank, not 0
    assert s.loc[10, "districts"] == 2
    assert s.index[0] == 10                                                              # fastest-warming first


def test_winter_sentence_wording():
    t = winter_sentence("Ludhiana", 91.2, 86.3, 4.0, -4.2)
    assert "about **91** in 1952-81" in t and "**86** in 1996-2025" in t and "5 fewer" in t
    assert "starts about 4 days later" in t and "ends about 4 days earlier" in t
    assert "earlier" in winter_sentence("X", 50, 60, -2.0, 1.0) and "10 more" in winter_sentence("X", 50, 60, -2, 1)
    assert "starts" not in winter_sentence("X", 30, 0, np.nan, np.nan)                  # no dates: no date claim
    assert winter_sentence("X", np.nan, 5, 1, 1).startswith("No winter record")


def test_state_table_names_and_order():
    st = pd.DataFrame({"state_id": [3, 32], "districts": [20, 14], "tmean_per_decade": [0.04, 0.14],
                       "tmin_per_decade": [0.11, 0.10], "tmax_per_decade": [-0.02, 0.19],
                       "cool_days_then": [91.2, 63.5], "cool_days_now": [86.2, 23.9], "start_shift_days": [3.8, 21.5],
                       "end_shift_days": [-4.2, -15.8], "wheat_yield_effect_pct": [-3.97, np.nan]})
    t = state_table(st, {3: "Punjab", 32: "Kerala"})
    assert list(t.State) == ["Kerala", "Punjab"]
    assert "Wheat already lost to warmer nights (%)" in t.columns
