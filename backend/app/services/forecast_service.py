"""Forecast serving (section 7).

- observed point: last known aqi on or before DEMO_NOW (horizon 0).
- tier 1 + model: federated GRU window prediction.
- tier 1 without model: persistence (last observed AQI for every horizon).
- tiers 2/3: inverse-distance-weighted mean of neighbor tier-1 forecasts.

Computed forecasts are cached in memory keyed by (city_id, model_version) and
the cache is cleared whenever a new model appears.
"""
import logging
import math
import threading

import numpy as np
import pandas as pd

from ..config import NEIGHBOR_RADIUS_KM, WINDOW_DAYS
from ..data.features import AQI_SCALE, build_feature_frame, build_windows, city_frame, scale_frame
from ..geo import haversine_km

logger = logging.getLogger("vayusetu.forecast")

_cache_lock = threading.Lock()
_cache: dict[tuple[str, str], dict] = {}
_model_state = {"version": None, "params": None}


def set_model(version: str | None, params) -> None:
    with _cache_lock:
        _model_state["version"] = version
        _model_state["params"] = params
        _cache.clear()


def model_info() -> tuple[str | None, object]:
    with _cache_lock:
        return _model_state["version"], _model_state["params"]


class ForecastUnavailable(Exception):
    pass


def _h_change_std(aqi_series: pd.Series, h: int) -> float:
    """Historical std of h-day AQI change; shared by persistence bounds."""
    change = (aqi_series - aqi_series.shift(h)).dropna()
    std = float(change.std()) if len(change) >= 2 else 15.0
    if math.isnan(std) or std <= 0:
        std = 15.0
    return std


def _add_days(date_str: str, days: int) -> str:
    from datetime import date, timedelta

    d = date.fromisoformat(date_str)
    return (d + timedelta(days=days)).isoformat()


def _window_pred_aqi(params, window_scaled: np.ndarray) -> list[float]:
    """Run the global GRU on one (WINDOW_DAYS, F) window; returns 3 AQI values."""
    import torch

    from ..federated.model import build_model, set_parameters

    model = build_model(0)
    set_parameters(model, params)
    model.eval()
    with torch.no_grad():
        x = torch.from_numpy(window_scaled.astype(np.float32)).unsqueeze(0)
        out = model(x)[0].numpy()
    return [float(np.clip(v * AQI_SCALE, 0.0, 500.0)) for v in out]


def _build_latest_window(store, city_id: str) -> tuple[np.ndarray | None, bool]:
    g = city_frame(store.master, city_id)
    if g.empty:
        return None, False
    ff = build_feature_frame(g)
    scaled = scale_frame(ff)

    demo_date = pd.Timestamp(store.demo_now)
    if demo_date not in scaled.index:
        # Use the latest available date on or before DEMO_NOW.
        idx = scaled.index[scaled.index <= demo_date]
        if len(idx) == 0:
            return None, False
        demo_date = idx[-1]
    t_pos = scaled.index.get_loc(demo_date)
    start = t_pos - WINDOW_DAYS + 1
    if start < 0:
        return None, False
    window = scaled.iloc[start:t_pos + 1]
    aqi_window = pd.to_numeric(g["aqi"], errors="coerce").reindex(scaled.index).iloc[start:t_pos + 1]
    valid_recent = bool(aqi_window.tail(3).notna().any())
    return window.to_numpy(dtype=np.float32), valid_recent


def _persistence_forecast(store, city_id: str) -> dict:
    aqi, _ = store.latest_aqi(city_id)
    if aqi is None:
        raise ForecastUnavailable(f"no observed AQI for {city_id}")
    # Bounds: +/- historical std of h-day AQI change for this city.
    g = store.master[store.master["city_id"] == city_id]
    aqi_series = g[g["aqi"].notna()].sort_values("date")["aqi"].astype(float)
    points = [{
        "date": store.demo_now, "horizon_days": 0,
        "predicted_aqi": round(aqi, 1),
        # Horizon-0 band: 1-day-change std is the honest proxy for the very
        # next-day spread; a hardcoded 5 understated it by an order of
        # magnitude on volatile days.
        "lower_bound": round(max(0.0, aqi - _h_change_std(aqi_series, 1)), 1),
        "upper_bound": round(min(500.0, aqi + _h_change_std(aqi_series, 1)), 1),
        "observed": True,
    }]
    for h in (1, 2, 3):
        std = _h_change_std(aqi_series, h)
        points.append({
            "date": _add_days(store.demo_now, h), "horizon_days": h,
            "predicted_aqi": round(aqi, 1),
            "lower_bound": round(max(0.0, aqi - std), 1),
            "upper_bound": round(min(500.0, aqi + std), 1),
            "observed": False,
        })
    return {"method": "persistence", "model_version": None, "points": points}


def _load_forecast_bounds() -> list[float] | None:
    """Per-horizon p90 residuals from forecast_bounds.json (section 7); a
    corrupt or missing file is treated as absent (section 12)."""
    import json
    import os

    path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed", "forecast_bounds.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return None
        vals = [float(data[str(h)]) for h in (1, 2, 3) if str(h) in data]
        return vals if len(vals) == 3 else None
    except Exception:
        return None


def _model_forecast(store, city_id: str, version: str, params) -> dict:
    window, valid_recent = _build_latest_window(store, city_id)
    if window is None:
        raise ForecastUnavailable(f"not enough recent data for {city_id}")
    if not valid_recent:
        # No valid aqi in the last 3 days of the window: persistence instead.
        fc = _persistence_forecast(store, city_id)
        return fc

    preds = _window_pred_aqi(params, window)

    residual_p90 = [15.0, 18.0, 21.0]
    bounds = _load_forecast_bounds()
    if bounds:
        residual_p90 = bounds

    aqi, _ = store.latest_aqi(city_id)
    points = [{
        "date": store.demo_now, "horizon_days": 0,
        "predicted_aqi": round(aqi, 1),
        "lower_bound": round(max(0.0, aqi - 5), 1), "upper_bound": round(min(500.0, aqi + 5), 1),
        "observed": True,
    }]
    for i, h in enumerate((1, 2, 3)):  # noqa: B007 (i used for residual index)
        pred = preds[i]
        q10 = residual_p90[i] if i < len(residual_p90) else 15.0
        lower = float(np.clip(pred - q10, 0.0, 500.0))
        upper = float(np.clip(pred + q10, 0.0, 500.0))
        points.append({
            "date": _add_days(store.demo_now, h), "horizon_days": h,
            "predicted_aqi": round(pred, 1),
            "lower_bound": round(lower, 1), "upper_bound": round(upper, 1),
            "observed": False,
        })
    return {"method": "federated_gru", "model_version": version, "points": points}


def _neighbor_forecast(store, city_id: str, tier: int) -> dict:
    entry = store.city(city_id)
    if entry is None:
        raise ForecastUnavailable(f"unknown city {city_id}")
    neighbors = []
    for other in store.active_cities():
        if other.city_id == city_id or store.tier_of(other.city_id) != 1:
            continue
        d = haversine_km(entry.latitude, entry.longitude, other.latitude, other.longitude)
        if d <= NEIGHBOR_RADIUS_KM:
            neighbors.append((other, d))
    if not neighbors:
        raise NoNeighbors(f"no monitored city within {int(NEIGHBOR_RADIUS_KM)} km")

    # Each neighbor uses its own tier-1 forecast (recursive but bounded:
    # neighbors are tier 1, which never re-enters the neighbor branch).
    neighbor_fcs = []
    for other, d in neighbors:
        nfc = _tier1_forecast(store, other.city_id)
        neighbor_fcs.append((nfc, d))

    version, _ = model_info()
    points = []
    for h in (0, 1, 2, 3):
        wsum = sum(1.0 / max(d, 10.0) ** 2 for _, d in neighbor_fcs)
        pred = 0.0
        lower = 0.0
        upper = 0.0
        for nfc, d in neighbor_fcs:
            w = (1.0 / max(d, 10.0) ** 2) / wsum
            pt = next((p for p in nfc["points"] if p["horizon_days"] == h), None)
            if pt is None:
                pt = nfc["points"][-1]
            pred += w * pt["predicted_aqi"]
            lower += w * pt["lower_bound"]
            upper += w * pt["upper_bound"]
        if h == 0:
            points.append({
                "date": store.demo_now, "horizon_days": 0,
                "predicted_aqi": round(pred, 1),
                "lower_bound": round(max(0.0, pred - 5), 1),
                "upper_bound": round(min(500.0, pred + 5), 1),
                "observed": True,
            })
        else:
            widen = 1.5
            center = pred
            half = max(upper - pred, pred - lower) * widen
            points.append({
                "date": _add_days(store.demo_now, h), "horizon_days": h,
                "predicted_aqi": round(center, 1),
                "lower_bound": round(max(0.0, center - half), 1),
                "upper_bound": round(min(500.0, center + half), 1),
                "observed": False,
            })
    return {"method": "neighbor_idw", "model_version": version, "points": points}


class NoNeighbors(ForecastUnavailable):
    pass


def _tier1_forecast(store, city_id: str) -> dict:
    """Tier-1 branch only: model when available, else persistence."""
    version, params = model_info()
    if version and params is not None:
        return _model_forecast(store, city_id, version, params)
    return _persistence_forecast(store, city_id)


def get_forecast(store, city_id: str) -> dict:
    """Public entry. Raises ForecastUnavailable (message goes in the envelope)."""
    version, params = model_info()
    tier = store.tier_of(city_id)
    key = (city_id, version or "none")

    with _cache_lock:
        if key in _cache:
            return _cache[key]

    if tier == 1:
        fc = _tier1_forecast(store, city_id)
    else:
        fc = _neighbor_forecast(store, city_id, tier)

    result = {"city_id": city_id, "tier": tier, **fc}
    with _cache_lock:
        _cache[key] = result
    return result
