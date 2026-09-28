"""Hotspots and wind-based downwind computation (section 8).

Wind convention: wind_dir is where wind comes FROM; it blows TOWARD
wind_dir + 180. Downwind city: nearest active city within 600 km whose bearing
from the hotspot is within 35 degrees of wind_toward, ETA <= 72 h.
"""
import logging
import math
from datetime import date, timedelta

import pandas as pd

from ..config import HORIZONS  # noqa: F401 (documentation of horizon linkage)
from ..geo import angular_diff, bearing_deg, haversine_km, wind_toward_deg

logger = logging.getLogger("vayusetu.hotspots")

TOP_FIRES = 12
FIRE_MAX_AGE_DAYS = 2
DOWNWIND_MAX_KM = 600.0
DOWNWIND_CONE_DEG = 35.0
MAX_ETA_H = 72.0


def _in_stubble_box(lat: float, lon: float) -> bool:
    return 29.0 <= lat <= 32.5 and 73.5 <= lon <= 77.8


def _fire_cause(lat: float, lon: float, detected: date) -> str:
    if _in_stubble_box(lat, lon) and detected.month in (10, 11, 4, 5):
        return "stubble_burning"
    return "open_burning"


def _wind_for_point(store, lat: float, lon: float) -> tuple[float | None, float | None]:
    """wind_dir (FROM) and wind_speed from the nearest city with weather on
    DEMO_NOW or the latest earlier date within 3 days."""
    if store.master is None or store.master.empty:
        return None, None
    demo = pd.Timestamp(store.demo_now)
    window = pd.date_range(end=demo, periods=4, freq="D").strftime("%Y-%m-%d").tolist()

    best_city, best_d = None, float("inf")
    for c in store.active_cities():
        d = haversine_km(lat, lon, c.latitude, c.longitude)
        if d < best_d:
            best_city, best_d = c, d

    if best_city is None:
        return None, None
    g = store.master[(store.master["city_id"] == best_city.city_id) & (store.master["date"].isin(window))]
    g = g[g["wind_dir"].notna() & g["wind_speed"].notna()].sort_values("date")
    if g.empty:
        return None, None
    row = g.iloc[-1]
    return float(row["wind_dir"]), float(row["wind_speed"])


def _downwind_city(store, lat: float, lon: float, wind_from: float, wind_speed: float):
    wind_toward = wind_toward_deg(wind_from)
    best = None
    best_d = float("inf")
    for c in store.active_cities():
        d = haversine_km(lat, lon, c.latitude, c.longitude)
        if d > DOWNWIND_MAX_KM:
            continue
        b = bearing_deg(lat, lon, c.latitude, c.longitude)
        if angular_diff(b, wind_toward) > DOWNWIND_CONE_DEG:
            continue
        if d < best_d:
            best, best_d = c, d
    if best is None:
        return None
    eta = best_d / (max(wind_speed, 1.0) * 3.6)
    if eta > MAX_ETA_H:
        return None
    return best, best_d, eta


def get_hotspots(store) -> list[dict]:
    hotspots: list[dict] = []
    if store.master is None:
        return hotspots

    # (a) fires: last 2 days, top 12 by frp
    fires = store.fires
    if fires is not None and len(fires):
        demo = pd.Timestamp(store.demo_now)
        cutoff = (demo - pd.Timedelta(days=FIRE_MAX_AGE_DAYS)).strftime("%Y-%m-%d")
        recent = fires[fires["date"] >= cutoff].copy()
        recent = recent.sort_values("frp", ascending=False).head(TOP_FIRES)
        for i, (_, r) in enumerate(recent.iterrows()):
            lat, lon = float(r["latitude"]), float(r["longitude"])
            detected = date.fromisoformat(str(r["date"]))
            wind_from, wind_speed = _wind_for_point(store, lat, lon)
            hotspot = {
                "id": f"fire-{r['date']}-{i}",
                "latitude": round(lat, 4),
                "longitude": round(lon, 4),
                "cause": _fire_cause(lat, lon, detected),
                "confidence": round(min(1.0, max(0.4, 0.4 + 0.6 * min(float(r["frp"]) / 100.0, 1.0))), 2),
                "detected_on": str(r["date"]),
                "frp": round(float(r["frp"]), 1),
                "wind_direction_deg": None, "wind_speed_ms": None, "wind_toward_deg": None,
                "downwind_city_id": None, "downwind_city_name": None,
                "distance_km": None, "eta_hours": None,
            }
            if wind_from is not None:
                toward = wind_toward_deg(wind_from)
                hotspot["wind_direction_deg"] = round(wind_from, 1)
                hotspot["wind_speed_ms"] = round(wind_speed, 1)
                hotspot["wind_toward_deg"] = round(toward, 1)
                hit = _downwind_city(store, lat, lon, wind_from, wind_speed)
                if hit is not None:
                    city, dist, eta = hit
                    hotspot["downwind_city_id"] = city.city_id
                    hotspot["downwind_city_name"] = city.name
                    hotspot["distance_km"] = round(dist, 1)
                    hotspot["eta_hours"] = round(eta, 1)
            hotspots.append(hotspot)

    # (b) industrial zones: all rows
    for z in store.zones:
        lat, lon = z["latitude"], z["longitude"]
        nearest_t1, _ = _nearest_tier1(store, lat, lon)
        pm25_ref = 75.0
        if nearest_t1 is not None:
            g = store.master[(store.master["city_id"] == nearest_t1.city_id)
                             & (store.master["pm25"].notna())]
            if len(g):
                row = g.loc[g[g["date"] <= store.demo_now]["date"].idxmax()] if (g["date"] <= store.demo_now).any() else g.iloc[-1]
                pm25_ref = float(row["pm25"])
        confidence = min(0.9, max(0.2, pm25_ref / 150.0))
        wind_from, wind_speed = _wind_for_point(store, lat, lon)
        hotspot = {
            "id": f"ind-{z['zone_id']}",
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "cause": "industrial",
            "confidence": round(confidence, 2),
            "detected_on": store.demo_now,
            "frp": None,
            "wind_direction_deg": None, "wind_speed_ms": None, "wind_toward_deg": None,
            "downwind_city_id": None, "downwind_city_name": None,
            "distance_km": None, "eta_hours": None,
        }
        if wind_from is not None:
            hotspot["wind_direction_deg"] = round(wind_from, 1)
            hotspot["wind_speed_ms"] = round(wind_speed, 1)
            hotspot["wind_toward_deg"] = round(wind_toward_deg(wind_from), 1)
            hit = _downwind_city(store, lat, lon, wind_from, wind_speed)
            if hit is not None:
                city, dist, eta = hit
                hotspot["downwind_city_id"] = city.city_id
                hotspot["downwind_city_name"] = city.name
                hotspot["distance_km"] = round(dist, 1)
                hotspot["eta_hours"] = round(eta, 1)
        hotspots.append(hotspot)

    return hotspots


def _nearest_tier1(store, lat: float, lon: float):
    best, best_d = None, float("inf")
    for c in store.active_cities():
        if store.tier_of(c.city_id) != 1:
            continue
        d = haversine_km(lat, lon, c.latitude, c.longitude)
        if d < best_d:
            best, best_d = c, d
    return best, best_d
