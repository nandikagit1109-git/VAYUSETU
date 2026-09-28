"""Feature pipeline tests (section 14.3): shapes, NaN, leakage, split."""
import numpy as np
import pandas as pd
import pytest

from app.data.features import (
    F, FEATURES, WINDOW_DAYS, build_feature_frame, build_windows,
    chronological_split, city_frame, scale_frame,
)


def _synthetic_city_frame(days: int = 120) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=days, freq="D")
    df = pd.DataFrame({
        "city_id": "delhi",
        "date": [d.strftime("%Y-%m-%d") for d in dates],
        "pm25": np.linspace(50, 150, days),
        "pm10": np.linspace(80, 240, days),
        "no2": np.linspace(20, 40, days),
        "so2": np.linspace(5, 15, days),
        "co": np.linspace(0.5, 1.5, days),
        "o3": np.linspace(40, 20, days),
        "aqi": np.linspace(100, 250, days),
        "temp": np.linspace(20, 30, days),
        "humidity": np.linspace(60, 40, days),
        "pressure": np.full(days, 100.0),
        "wind_speed": np.linspace(3, 5, days),
        "wind_dir": np.linspace(200, 300, days),
        "fire_count": np.zeros(days),
        "fire_frp": np.zeros(days),
        "s5p_no2_umol_m2": np.linspace(50, 90, days),
        "s5p_so2_umol_m2": np.linspace(30, 50, days),
        "s5p_co_mmol_m2": np.linspace(29, 32, days),
        "aerosol_index": np.linspace(0.7, 1.5, days),
    })
    df.index = dates
    df.index.name = "date_dt"
    return df


def test_window_shape():
    g = _synthetic_city_frame(120)
    X, y, end_dates = build_windows(g)
    assert X.ndim == 3
    assert X.shape[1:] == (WINDOW_DAYS, F)  # (N, 14, 23)
    assert y.shape[0] == X.shape[0]
    assert y.shape[1] == 3
    assert len(end_dates) == X.shape[0]


def test_no_nan_after_imputation():
    g = _synthetic_city_frame(120)
    # Punch holes in every feature including satellite NaNs.
    g.loc[g.index[10:14], "s5p_no2_umol_m2"] = np.nan
    g.loc[g.index[30:31], "temp"] = np.nan
    g.loc[g.index[50:55], "wind_dir"] = np.nan
    ff = build_feature_frame(g)
    scaled = scale_frame(ff)
    assert not scaled[FEATURES].isna().any().any()


def test_no_target_leakage():
    g = _synthetic_city_frame(120)
    X, y, end_dates = build_windows(g)
    aqi = pd.to_numeric(g["aqi"], errors="coerce")
    for i in range(X.shape[0]):
        t = end_dates[i]
        t_pos = g.index.get_loc(t)
        # Targets are strictly AFTER the last input day.
        assert y[i, 0] * 500 == pytest.approx(aqi.iloc[t_pos + 1], abs=0.01)
        assert y[i, 2] * 500 == pytest.approx(aqi.iloc[t_pos + 3], abs=0.01)


def test_gap_does_not_shift_windows():
    """A missing day must become an explicit NaN row, not shift the index."""
    g = _synthetic_city_frame(120)
    dropped = g.drop(g.index[60])  # remove one day entirely
    cf = city_frame(dropped.assign(city_id="delhi"), "delhi")
    # city_frame reindexes to a contiguous daily range: one NaN row appears.
    assert len(cf) == 120
    assert cf["aqi"].iloc[60:61].isna().all()


def test_chronological_split_no_overlap():
    g = _synthetic_city_frame(200)
    X, y, end_dates = build_windows(g)
    X_tr, y_tr, X_val, y_val = chronological_split(X, y)
    assert X_tr.shape[0] + X_val.shape[0] == X.shape[0]
    # Chronological: validation end dates come strictly after training ones.
    assert end_dates[X_tr.shape[0] - 1] < end_dates[X_tr.shape[0]]
