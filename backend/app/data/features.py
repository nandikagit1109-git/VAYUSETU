"""Feature engineering (section 5.7).

Feature order (F = 23) is FIXED. Scaling is a fixed global (offset, scale)
table — a constant, not per-city statistics, so no city ever shares statistics
across the federated boundary: scaled = clip((x - offset) / scale, -3, 3).
Missing handling per city, in this exact order: ffill up to 3 days, then
remaining NaN -> 0 AFTER scaling. Never bfill (leaks the future).
"""
import numpy as np
import pandas as pd

from ..config import HORIZONS, WINDOW_DAYS

F = 23
FEATURES = [
    "pm25", "pm10", "no2", "so2", "co", "o3", "aqi",
    "temp", "humidity", "pressure", "wind_speed", "wind_dir_sin", "wind_dir_cos",
    "fire_count", "fire_frp",
    "s5p_no2_umol_m2", "s5p_so2_umol_m2", "s5p_co_mmol_m2", "aerosol_index",
    "doy_sin", "doy_cos", "dow_sin", "dow_cos",
]

# (offset, scale) per raw feature, from section 5.7.
SCALING = {
    "pm25": (0.0, 250.0), "pm10": (0.0, 400.0), "no2": (0.0, 100.0), "so2": (0.0, 50.0),
    "co": (0.0, 5.0), "o3": (0.0, 100.0), "aqi": (0.0, 500.0),
    "temp": (25.0, 15.0), "humidity": (50.0, 50.0), "pressure": (100.0, 10.0),
    "wind_speed": (0.0, 10.0), "fire_count": (0.0, 50.0), "fire_frp": (0.0, 500.0),
    "s5p_no2_umol_m2": (0.0, 150.0), "s5p_so2_umol_m2": (0.0, 200.0),
    "s5p_co_mmol_m2": (0.0, 50.0), "aerosol_index": (0.0, 3.0),
    # wind_dir_sin/cos and calendar features are already in [-1, 1]; the generic
    # (0, 1) transform leaves them untouched apart from clipping.
    "wind_dir_sin": (0.0, 1.0), "wind_dir_cos": (0.0, 1.0),
    "doy_sin": (0.0, 1.0), "doy_cos": (0.0, 1.0),
    "dow_sin": (0.0, 1.0), "dow_cos": (0.0, 1.0),
}

AQI_SCALE = 500.0
MAX_FFILL = 3


def city_frame(master: pd.DataFrame, city_id: str) -> pd.DataFrame:
    """One city's rows, sorted by date, reindexed to a contiguous daily range
    so gaps become explicit NaN rows instead of silently shifting windows."""
    g = master[master["city_id"] == city_id].copy()
    if g.empty:
        return g
    g["date_dt"] = pd.to_datetime(g["date"])
    g.index.name = None  # avoid an ambiguous index/column name clash
    g = g.sort_values("date_dt").drop_duplicates(subset="date_dt").set_index("date_dt")
    full_index = pd.date_range(g.index.min(), g.index.max(), freq="D")
    g = g.reindex(full_index)
    g.index.name = "date_dt"
    return g


def _calendar_features(index: pd.DatetimeIndex) -> dict[str, np.ndarray]:
    doy = np.array([ts.dayofyear for ts in index], dtype=float)
    dow = np.array([ts.dayofweek for ts in index], dtype=float)
    return {
        "doy_sin": np.sin(2 * np.pi * doy / 365.0),
        "doy_cos": np.cos(2 * np.pi * doy / 365.0),
        "dow_sin": np.sin(2 * np.pi * dow / 7.0),
        "dow_cos": np.cos(2 * np.pi * dow / 7.0),
    }


def build_feature_frame(g: pd.DataFrame) -> pd.DataFrame:
    """Adds wind_dir sin/cos + calendar features; keeps only FEATURES columns."""
    out = pd.DataFrame(index=g.index)
    for col in FEATURES:
        if col in ("wind_dir_sin", "wind_dir_cos"):
            continue
        out[col] = pd.to_numeric(g[col], errors="coerce") if col in g.columns else np.nan
    if "wind_dir" in g.columns:
        wd = np.radians(pd.to_numeric(g["wind_dir"], errors="coerce"))
        out["wind_dir_sin"] = np.sin(wd)
        out["wind_dir_cos"] = np.cos(wd)
    else:
        out["wind_dir_sin"] = np.nan
        out["wind_dir_cos"] = np.nan
    out.update({k: v for k, v in _calendar_features(g.index).items()})
    return out[FEATURES]


def scale_frame(ff: pd.DataFrame) -> pd.DataFrame:
    scaled = ff.copy()
    for col in FEATURES:
        offset, scale = SCALING[col]
        scaled[col] = ((ff[col] - offset) / scale).clip(-3.0, 3.0)
    # Per-city missing handling: ffill up to MAX_FFILL days, then 0 after scaling.
    scaled = scaled.ffill(limit=MAX_FFILL)
    return scaled.fillna(0.0)


def build_windows(g: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    """Windows for one city.

    Returns (X, y, dates_end) where X has shape (N, WINDOW_DAYS, F), y has
    shape (N, len(HORIZONS)) in AQI units (already divided by 500 at the caller's
    discretion — here raw AQI targets are returned so evaluate.py can reuse
    them), and dates_end[i] is the date of the last input day of sample i.

    Sample i uses days [i, i+WINDOW_DAYS) as input; targets are aqi at
    t+1, t+2, t+3 where t is the last input day. Samples with any NaN target
    are dropped. Rows without any AQI in the whole city series are unusable
    for targets, which the NaN check handles naturally.
    """
    ff = build_feature_frame(g)
    scaled = scale_frame(ff)

    aqi = pd.to_numeric(g["aqi"], errors="coerce") if "aqi" in g.columns else pd.Series(np.nan, index=g.index)
    n = len(scaled)
    max_h = max(HORIZONS)
    X_list, y_list, end_dates = [], [], []
    aqi_values = aqi.to_numpy(dtype=float)
    dates = g.index

    for i in range(0, n - WINDOW_DAYS + 1):
        t = i + WINDOW_DAYS - 1  # last input day
        if t + max_h >= n:
            break
        targets = [aqi_values[t + h] for h in HORIZONS]
        if any((v != v) for v in targets):  # NaN check
            continue
        X_list.append(scaled[FEATURES].iloc[i:i + WINDOW_DAYS].to_numpy(dtype=np.float32))
        y_list.append([v / AQI_SCALE for v in targets])
        end_dates.append(dates[t])

    if not X_list:
        return (np.empty((0, WINDOW_DAYS, F), dtype=np.float32),
                np.empty((0, len(HORIZONS)), dtype=np.float32),
                np.empty(0, dtype="datetime64[ns]"))
    return np.stack(X_list), np.asarray(y_list, dtype=np.float32), pd.DatetimeIndex(end_dates)


def chronological_split(X: np.ndarray, y: np.ndarray, train_frac: float = 0.8):
    """First train_frac of samples train, the rest validate. Never shuffled
    across the split (the trainer shuffles the training set within an epoch,
    seeded)."""
    n = X.shape[0]
    n_train = max(1, int(n * train_frac))
    if n_train >= n:
        n_train = n - 1 if n > 1 else n
    return X[:n_train], y[:n_train], X[n_train:], y[n_train:]
