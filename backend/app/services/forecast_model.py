"""Simple trained time-series model for the 72-hour AQI forecast.

The model is a ridge-regularised linear regression (closed-form least squares,
deterministic) trained per city on the bundled historical CSV. Features:
hour-of-day sin/cos, day-of-week sin/cos and the AQI lag-24h value.

DEMO NOTE: "now" for the forecast is the last timestamp of the fixed seed CSV
(not the wall clock). This keeps charts and alert behaviour identical on every
run — required for rehearsal — and the "next 24h" alert window is the first 24
forecast points.
"""
import logging
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from ..config import DATA_DIR

logger = logging.getLogger("vayusetu.forecast_model")

FORECAST_HOURS = 72
AQI_SCALE = 500.0
RIDGE_LAMBDA = 1.0


class ForecastUnavailable(Exception):
    """Raised when a city has no trained model (missing/invalid data)."""


def _features(ts: pd.Series, lag24: np.ndarray) -> np.ndarray:
    hod = ts.dt.hour.to_numpy(dtype=float)
    dow = ts.dt.dayofweek.to_numpy(dtype=float)
    return np.column_stack([
        np.ones(len(ts)),
        np.sin(2 * np.pi * hod / 24.0),
        np.cos(2 * np.pi * hod / 24.0),
        np.sin(2 * np.pi * dow / 7.0),
        np.cos(2 * np.pi * dow / 7.0),
        lag24,
    ])


class CityForecastModel:
    def __init__(self, city: str):
        path = DATA_DIR / f"historical_aqi_{city}.csv"
        df = pd.read_csv(path)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)
        if len(df) < 48:
            raise ForecastUnavailable(f"not enough history for {city}")
        aqi = df["aqi"].to_numpy(dtype=float)
        lag24_all = np.concatenate([aqi[:24], aqi[:-24]]) / AQI_SCALE
        X = _features(df["timestamp"], lag24_all)
        y = aqi / AQI_SCALE

        n_features = X.shape[1]
        A = X.T @ X + RIDGE_LAMBDA * np.eye(n_features)
        A[0, 0] -= RIDGE_LAMBDA  # do not penalise the intercept
        self.weights = np.linalg.solve(A, X.T @ y)
        resid_std = float(np.std(y - X @ self.weights)) * AQI_SCALE
        self.resid_std = max(4.0, resid_std)
        self.history = df

    def predict(self) -> tuple[datetime, list[dict]]:
        """Returns (base_time, 72 hourly forecast points)."""
        last_ts = self.history["timestamp"].iloc[-1]
        base = last_ts.to_pydatetime().replace(tzinfo=timezone.utc)
        last_values = list(self.history["aqi"].to_numpy(dtype=float)[-24:])

        points: list[dict] = []
        for h in range(1, FORECAST_HOURS + 1):
            ts = base + timedelta(hours=h)
            lag24 = last_values[len(last_values) - 24] / AQI_SCALE
            x = np.array([[
                1.0,
                np.sin(2 * np.pi * ts.hour / 24.0),
                np.cos(2 * np.pi * ts.hour / 24.0),
                np.sin(2 * np.pi * ts.weekday() / 7.0),
                np.cos(2 * np.pi * ts.weekday() / 7.0),
                lag24,
            ]])
            pred = float(np.clip(x @ self.weights, 0.02, 1.0)) * AQI_SCALE
            pred = float(np.clip(pred, 5.0, 500.0))
            band = min(120.0, 1.28 * self.resid_std * np.sqrt(1.0 + h / 24.0))
            points.append({
                "forecast_for": ts,
                "predicted_aqi": round(pred, 1),
                "lower_bound": round(max(0.0, pred - band), 1),
                "upper_bound": round(min(500.0, pred + band), 1),
            })
            last_values.append(pred)
        return base, points


_cache: dict[str, CityForecastModel] = {}


def get_forecast(city: str) -> dict:
    """Train (once) and run the forecast for a city. Raises
    ForecastUnavailable for unknown cities or unusable data."""
    city = city.strip().lower()
    known = {"delhi", "kanpur", "pune"}
    if city not in known:
        raise ForecastUnavailable(f"no forecast model for city '{city}'")
    if city not in _cache:
        try:
            _cache[city] = CityForecastModel(city)
        except Exception as exc:
            logger.warning("forecast model training failed for %s: %s", city, exc)
            raise ForecastUnavailable(f"forecast pending for {city}") from exc
    base, points = _cache[city].predict()
    generated_at = datetime.now(timezone.utc)
    return {
        "city": city,
        "base_time": base,
        "generated_at": generated_at,
        "points": [
            {
                "forecast_for": p["forecast_for"].isoformat(),
                "predicted_aqi": p["predicted_aqi"],
                "lower_bound": p["lower_bound"],
                "upper_bound": p["upper_bound"],
            }
            for p in points
        ],
        "raw_points": points,  # datetimes, for DB persistence
    }
