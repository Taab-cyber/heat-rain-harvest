"""Leakage test: the train-only yield trend must ignore test years completely.

Run from the project root:  python -m pytest tests/  (or: python tests/test_no_leakage.py)
"""
import numpy as np
import pandas as pd
import pytest

from src.config import PROCESSED, TRAIN_LAST_YEAR
from src.features import detrend_train_only


DATA = PROCESSED / "model_wheat.parquet"


@pytest.mark.skipif(not DATA.exists(), reason="needs data/processed (run the pipeline first)")
def test_train_trend_ignores_test_years():
    m = pd.read_parquet(DATA)
    a = detrend_train_only(m)
    m2 = m.copy()
    m2.loc[m2.year > TRAIN_LAST_YEAR, "yield_t_ha"] = 999.0     # wreck every test-year yield
    b = detrend_train_only(m2)
    assert np.allclose(a.trend_train, b.trend_train, equal_nan=True)


if __name__ == "__main__":
    test_train_trend_ignores_test_years()
    print("ok")
