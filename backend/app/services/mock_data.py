"""Bundled mock datasets (satellite fire hotspots + wind), loaded at startup.

Everything here is offline-safe: if a JSON file is missing or malformed we log
a warning and fall back to built-in defaults instead of crashing.
"""
import json
import logging
import math

from ..config import CITIES, DATA_DIR

logger = logging.getLogger("vayusetu.mock_data")

_DEFAULT_HOTSPOTS: list[dict] = [
    {"latitude": 30.70, "longitude": 75.90, "cause": "stubble_burning", "confidence": 0.91, "detected_at": "2026-09-20T06:00:00+00:00"},
    {"latitude": 30.30, "longitude": 76.20, "cause": "stubble_burning", "confidence": 0.87, "detected_at": "2026-09-20T07:30:00+00:00"},
    {"latitude": 26.50, "longitude": 80.05, "cause": "industrial", "confidence": 0.88, "detected_at": "2026-09-22T04:00:00+00:00"},
]

_DEFAULT_WIND_REGIONS: list[dict] = [
    {"name": "punjab_haryana", "center_lat": 30.20, "center_lon": 75.90, "radius_km": 320.0, "direction_from_deg": 315.0, "speed_kmh": 14.0},
    {"name": "kanpur_industrial", "center_lat": 26.45, "center_lon": 80.10, "radius_km": 160.0, "direction_from_deg": 270.0, "speed_kmh": 11.0},
]

_hotspots_cache: list[dict] | None = None
_wind_cache: list[dict] | None = None


def _load_json(path, fallback, label):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:  # missing/corrupt file must never crash the app
        logger.warning("could not load %s from %s (%s); using built-in defaults", label, path, exc)
        return fallback


def preload() -> None:
    """Load datasets once at startup so later requests never touch disk."""
    get_fire_hotspots()
    get_wind_regions()


def get_fire_hotspots() -> list[dict]:
    global _hotspots_cache
    if _hotspots_cache is None:
        data = _load_json(DATA_DIR / "fire_hotspots_mock.json", {"hotspots": _DEFAULT_HOTSPOTS}, "fire hotspots")
        try:
            _hotspots_cache = list(data["hotspots"])
        except Exception:
            logger.warning("malformed fire_hotspots_mock.json; using built-in defaults")
            _hotspots_cache = list(_DEFAULT_HOTSPOTS)
    return _hotspots_cache


def get_wind_regions() -> list[dict]:
    global _wind_cache
    if _wind_cache is None:
        data = _load_json(DATA_DIR / "wind_data_mock.json", {"regions": _DEFAULT_WIND_REGIONS}, "wind data")
        try:
            _wind_cache = list(data["regions"])
        except Exception:
            logger.warning("malformed wind_data_mock.json; using built-in defaults")
            _wind_cache = list(_DEFAULT_WIND_REGIONS)
    return _wind_cache


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial compass bearing (0-360, clockwise from north) from point 1 to 2."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def angular_diff(a: float, b: float) -> float:
    d = abs(a - b) % 360.0
    return 360.0 - d if d > 180.0 else d


def nearest_wind_region(lat: float, lon: float) -> dict:
    """Pick the wind region whose center is nearest to the given location."""
    regions = get_wind_regions()
    best, best_d = None, float("inf")
    for r in regions:
        d = haversine_km(lat, lon, r["center_lat"], r["center_lon"])
        if d < best_d:
            best, best_d = r, d
    return best or _DEFAULT_WIND_REGIONS[0]


def wind_for_location(lat: float, lon: float) -> dict:
    """Wind fields for a location, joined at request time (never stored).

    wind_direction_deg is the compass bearing the wind blows TOWARD.
    downwind_city is the demo city best aligned with that bearing.
    """
    region = nearest_wind_region(lat, lon)
    direction_toward = (float(region["direction_from_deg"]) + 180.0) % 360.0
    speed = float(region["speed_kmh"])

    best_city, best_dist = None, float("inf")
    for city, (clat, clon) in CITIES.items():
        dist = haversine_km(lat, lon, clat, clon)
        to_city = bearing_deg(lat, lon, clat, clon)
        diff = angular_diff(direction_toward, to_city)
        # Plumes hit the NEAREST city inside the wind cone, not the most
        # perfectly aligned one — that's the physically plausible downwind city.
        if diff <= 60.0 and dist < best_dist:
            best_city, best_dist = city, dist

    downwind_city = best_city
    eta_hours = round(best_dist / speed, 1) if (downwind_city is not None and speed > 0) else None
    return {
        "wind_direction_deg": round(direction_toward, 1),
        "wind_speed_kmh": speed,
        "downwind_city": downwind_city,
        "eta_hours": eta_hours,
    }
