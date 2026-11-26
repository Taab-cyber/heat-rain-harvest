"""Unit tests on small synthetic data: they run without the raw or processed data files.

Run from the project root:  python -m pytest tests/
"""
import numpy as np
import pandas as pd
import pytest

from src.features import _fit_line, crop_features, detrend_train_only, season_mask
from src.models import twoway_demean


# ------------------------------------------------------------------ seasons
def test_wheat_season_labelled_by_sowing_year():
    d = pd.Series(pd.to_datetime(["2021-11-01", "2021-12-31", "2022-01-15", "2022-03-31", "2022-04-01", "2021-10-31"]))
    assert season_mask(d, "Wheat").tolist()[:4] == [2021, 2021, 2021, 2021]
    assert season_mask(d, "Wheat").iloc[4:].isna().all()          # April and October are outside the season


def test_rice_season_is_june_to_october():
    d = pd.Series(pd.to_datetime(["2020-05-31", "2020-06-01", "2020-10-31", "2020-11-01"]))
    s = season_mask(d, "Rice")
    assert s.isna().tolist() == [True, False, False, True]


# ------------------------------------------------------------------ incomplete seasons
def _wheat_daily(missing_feb_share: float) -> pd.DataFrame:
    dates = pd.date_range("2021-11-01", "2022-03-31", freq="D")
    rng = np.random.default_rng(0)
    d = pd.DataFrame({"unit_id": 1, "date": dates, "tmax": 25 + rng.normal(0, 2, len(dates)),
                      "tmin": 10 + rng.normal(0, 2, len(dates)), "rain": rng.gamma(0.5, 2, len(dates))})
    feb = d.index[d.date.dt.month == 2]
    d.loc[feb[: int(len(feb) * missing_feb_share)], "tmax"] = np.nan
    return d


def test_incomplete_season_masks_every_temperature_feature():
    """Bug fixed in D23: feb_tmax_mean was not masked because its prefix ('feb_') was missing."""
    f = crop_features(_wheat_daily(0.9), "Wheat")                  # ~25 of 151 days missing -> > 10%
    for col in ("tmax_mean", "mar_tmax_mean", "feb_tmax_mean", "edd30_feb_mar"):
        assert f[col].isna().all(), col


def test_complete_season_keeps_features():
    f = crop_features(_wheat_daily(0.0), "Wheat")
    assert f[["tmax_mean", "feb_tmax_mean", "rain_total"]].notna().all().all()


# ------------------------------------------------------------------ detrending
def test_fit_line_needs_eight_years():
    assert np.isnan(_fit_line(np.arange(7.0), np.arange(7.0))[0])
    a, b = _fit_line(np.arange(2000.0, 2010.0), 2 + 0.1 * (np.arange(2000.0, 2010.0) - 2000))
    assert b == pytest.approx(0.1)


def test_train_trend_ignores_test_years_synthetic():
    years = np.arange(1997, 2023)
    m = pd.DataFrame({"unit_id": 1, "year": years, "yield_t_ha": 2 + 0.05 * (years - 1997)})
    a = detrend_train_only(m, 2017)
    m2 = m.copy()
    m2.loc[m2.year > 2017, "yield_t_ha"] = 999.0
    b = detrend_train_only(m2, 2017)
    assert np.allclose(a.trend_train, b.trend_train)
    assert np.allclose(a.yield_rel_anom_train, 0)                  # a perfect line has no anomaly


# ------------------------------------------------------------------ two-way fixed effects (D23)
def _panel(seed: int = 1, drop: float = 0.2):
    rng = np.random.default_rng(seed)
    unit, year = np.meshgrid(np.arange(60), np.arange(26), indexing="ij")
    p = pd.DataFrame({"unit": unit.ravel(), "year": year.ravel()})
    p = p.sample(frac=1 - drop, random_state=seed).reset_index(drop=True)          # unbalanced panel
    shock = rng.normal(0, 1, 26)                                                    # national year shock
    p["heat"] = rng.normal(0, 1, len(p)) + 2 * shock[p.year]                        # hot years are bad years...
    p["y"] = -0.05 * p.heat - 0.3 * shock[p.year] + rng.normal(0, 0.5, 60)[p.unit] + rng.normal(0, 0.02, len(p))
    return p                                                                        # ...for reasons other than heat


def test_twoway_demean_removes_both_means():
    p = _panel()
    z = twoway_demean(p[["heat", "y"]], p.unit.to_numpy(), p.year.to_numpy())
    assert np.abs(z.groupby(p.unit).mean().to_numpy()).max() < 1e-8
    assert np.abs(z.groupby(p.year).mean().to_numpy()).max() < 1e-8


def test_twoway_fe_matches_dummy_regression():
    import statsmodels.formula.api as smf
    p = _panel()
    z = twoway_demean(p[["heat", "y"]], p.unit.to_numpy(), p.year.to_numpy())
    b_demean = (z.heat * z.y).sum() / (z.heat ** 2).sum()
    b_dummies = smf.ols("y ~ heat + C(unit) + C(year)", data=p).fit().params["heat"]
    assert b_demean == pytest.approx(b_dummies, rel=1e-6)


def test_year_effects_stop_year_shocks_posing_as_heat():
    """The reason for D23: without year effects, a national bad-year shock is credited to heat."""
    p = _panel()
    within_unit = p[["heat", "y"]] - p.groupby("unit")[["heat", "y"]].transform("mean")
    b_unit_only = (within_unit.heat * within_unit.y).sum() / (within_unit.heat ** 2).sum()
    z = twoway_demean(p[["heat", "y"]], p.unit.to_numpy(), p.year.to_numpy())
    b_twoway = (z.heat * z.y).sum() / (z.heat ** 2).sum()
    assert b_twoway == pytest.approx(-0.05, abs=0.005)            # true effect recovered
    assert b_unit_only < -0.08                                     # district-only FE badly overstates it
