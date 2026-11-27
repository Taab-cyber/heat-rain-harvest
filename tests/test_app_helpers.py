"""Tests for the app's helper functions (app/helpers.py, app/report_pdf.py) on small synthetic tables.
They need no data files.  Run from the project root:  python -m pytest tests/
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from helpers import (advice_keys, district_panel, district_summary, drought_bad_years, latin1,  # noqa: E402
                     risk_level, risk_scores, season)


def _tables():
    years = np.arange(1997, 2023)
    rows = []
    for uid, bad_years in ((1, {2000, 2005, 2010, 2014, 2015}), (2, {2002})):
        for crop in ("Wheat", "Rice (monsoon)"):
            for yr in years:
                anom = -0.2 if yr in bad_years else 0.02
                rows.append({"unit_id": uid, "crop": crop, "year": yr, "area_ha": 1000.0, "yield_t_ha": 3 * (1 + anom),
                             "trend_full": 3.0, "yield_rel_anom": anom, "irr_share": 0.4 if uid == 1 else 0.95})
    yields = pd.DataFrame(rows)
    districts = pd.DataFrame({"unit_id": [1, 2, 3], "d_name": ["Alpha", "Beta", "Gamma"], "state_id": [3, 9, 9],
                              "risk_prob_high": [np.nan, np.nan, 0.7],
                              "risk_label_source": ["observed", "observed", "propagated"]})
    climate = yields[["unit_id", "crop", "year"]].copy()
    climate["tmin_mean"] = 8.0
    climate["rain_jun_sep"] = np.where(climate.year.isin([2000, 2005, 2010]), 400.0, 900.0)
    sens = pd.DataFrame({"unit_id": [1, 2, 1, 2], "crop": ["Wheat", "Wheat", "Rice (monsoon)", "Rice (monsoon)"],
                         "heat_effect_per_c": [-0.06, -0.03, -0.04, -0.02]})
    scen = pd.DataFrame([{"unit_id": u, "crop": c, "delta_c": d, "delta_rel_yield": -0.05 * d}
                         for u in (1, 2) for c in ("Wheat", "Rice (monsoon)") for d in (0.5, 1.0, 1.5, 2.0)])
    return yields, districts, climate, sens, scen


def test_season_label():
    assert season(2014) == "2014-15"
    assert season(1999) == "1999-00"


@pytest.mark.parametrize("share,level", [(0.0, "low"), (0.149, "low"), (0.15, "medium"), (0.29, "medium"),
                                         (0.30, "high"), (np.nan, "na"), (None, "na")])
def test_risk_level(share, level):
    assert risk_level(share) == level


def test_risk_scores_observed_and_propagated():
    yields, districts, *_ = _tables()
    r = risk_scores(yields, districts, "Wheat").set_index("unit_id")
    # district 1: bad years 2000, 2005, 2010, 2014, 2015 of 21 seasons up to 2017
    assert r.loc[1, "risk_score"] == pytest.approx(5 / 21)
    assert r.loc[1, "risk_source"] == "observed" and pd.isna(r.loc[1, "high_risk_chance_est"])
    # district 3 has no yields: the propagated probability is a different quantity, so it must NOT become a risk score
    assert pd.isna(r.loc[3, "risk_score"])
    assert r.loc[3, "high_risk_chance_est"] == pytest.approx(0.7)
    assert r.loc[3, "risk_source"] == "estimated from similar districts"
    r_rice = risk_scores(yields, districts, "Rice (monsoon)").set_index("unit_id")
    assert pd.isna(r_rice.loc[3, "risk_score"]) and pd.isna(r_rice.loc[3, "high_risk_chance_est"])  # wheat only


def test_district_summary_columns_and_units():
    yields, districts, _, sens, scen = _tables()
    s = district_summary(districts, yields, sens, scen, {3: "Punjab", 9: "Uttar Pradesh"})
    assert list(s.columns) == ["unit_id", "district", "state", "crop", "seasons", "mean_yield_t_ha", "risk_score_pct",
                               "risk_source", "high_risk_chance_pct_est", "heat_effect_pct_per_1C",
                               "change_pct_at_plus_1C", "change_pct_at_plus_2C"]
    assert len(s) == 4                                               # 2 districts x 2 crops
    a = s[(s.unit_id == 1) & (s.crop == "Wheat")].iloc[0]
    assert a.district == "Alpha" and a.state == "Punjab" and a.seasons == 26
    assert a.heat_effect_pct_per_1C == pytest.approx(-6.0)
    assert a.change_pct_at_plus_2C == pytest.approx(-10.0)
    assert a.risk_score_pct == pytest.approx(100 * 5 / 21, abs=1e-3)


def test_district_panel_merges_weather_and_flags_bad_years():
    yields, districts, climate, *_ = _tables()
    p = district_panel(yields, climate, districts, "Rice (monsoon)", {3: "Punjab", 9: "Uttar Pradesh"})
    assert len(p) == 2 * 26 and "crop" not in p
    assert {"district", "state", "season", "rain_jun_sep", "bad_year"} <= set(p.columns)
    r = p[(p.unit_id == 2) & (p.year == 2002)].iloc[0]
    assert bool(r.bad_year) and r.season == "2002-03" and r.state == "Uttar Pradesh"


def test_drought_bad_years_counts_only_dry_bad_years():
    yields, _, climate, *_ = _tables()
    y1 = yields[(yields.unit_id == 1) & (yields.crop == "Rice (monsoon)")]
    c1 = climate[(climate.unit_id == 1) & (climate.crop == "Rice (monsoon)")]
    assert drought_bad_years(y1, c1) == 3                            # 2000, 2005, 2010 were dry; 2014, 2015 not
    assert drought_bad_years(y1, c1.drop(columns="rain_jun_sep")) == 0


def test_advice_wheat_heat_needs_risk_and_march_heat():
    k = advice_keys("Wheat", 0.30, march_heat_pct=0.9, irr_share=0.95, drought_bad=0)
    assert k[0] == "wheat_heat" and "insurance" in k and "advisory" in k
    assert "wheat_heat" not in advice_keys("Wheat", 0.30, march_heat_pct=0.2, irr_share=0.95, drought_bad=0)
    assert "wheat_heat" not in advice_keys("Wheat", 0.05, march_heat_pct=0.9, irr_share=0.95, drought_bad=0)


def test_advice_rice_drought_and_water():
    k = advice_keys("Rice (monsoon)", 0.2, march_heat_pct=None, irr_share=0.3, drought_bad=3)
    assert k[:2] == ["rice_drought", "water"] and "insurance" in k
    assert "rice_drought" not in advice_keys("Wheat", 0.2, None, 0.3, drought_bad=3)


def test_advice_always_two_to_four_unique_items():
    for args in (("Wheat", 0.0, 0.1, 1.0, 0), ("Wheat", 0.5, 0.9, 0.1, 0), ("Rice (monsoon)", 0.5, None, 0.1, 5),
                 ("Rice (monsoon)", np.nan, None, np.nan, 0)):
        k = advice_keys(*args)
        assert 2 <= len(k) <= 4 and len(k) == len(set(k))


def test_latin1_replaces_unicode_minus_and_dashes():
    assert latin1("−5% – 3 °C ≥ 2") == "-5% - 3 °C >= 2"
    latin1("ਪੰਜਾਬੀ").encode("latin-1")                               # never raises


def test_pdf_report_is_a_one_page_pdf():
    pytest.importorskip("fpdf")
    pytest.importorskip("matplotlib")
    from report_pdf import district_pdf
    yields, *_ = _tables()
    y = yields[(yields.unit_id == 1) & (yields.crop == "Wheat")]
    pdf = district_pdf("Alpha", "Punjab", "Wheat", "wheat", "medium", 5, 26, 3.0, [("2014-15", 20.0)], -0.06, 2.0,
                       -0.10, (-0.168, -0.032), [("Sow on time.", "PAU: https://www.pau.edu/")],
                       "General guidance only.", y)
    import re
    assert pdf[:5] == b"%PDF-"
    assert len(re.findall(rb"/Type\s*/Page(?!s)", pdf)) == 1          # exactly one A4 page
    assert len(pdf) > 5000                                           # includes the chart image
