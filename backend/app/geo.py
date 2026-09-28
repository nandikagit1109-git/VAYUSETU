"""Geospatial primitives (section 8). Units and conventions are fixed:

- Distances in kilometres, Earth radius 6371.0088.
- All bearings in degrees clockwise from north, 0-360.
- wind_dir is the direction the wind blows FROM (meteorological convention,
  matching NASA POWER WD10M); the direction it blows TOWARD is +180.
"""
import math

from .config import FIRE_RADIUS_KM

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    a = min(1.0, max(0.0, a))
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial compass bearing from point 1 to point 2 (degrees 0-360)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def angular_diff(a: float, b: float) -> float:
    """Absolute smallest angle between two bearings (0-180)."""
    d = abs((a - b + 180.0) % 360.0) - 180.0
    return abs(d)


def wind_toward_deg(wind_from_deg: float) -> float:
    """Wind blows TOWARD wind_dir + 180. The classic mix-up; tested explicitly."""
    return (wind_from_deg + 180.0) % 360.0


def nearest_city(lat: float, lon: float, cities: list[dict]) -> tuple[dict | None, float]:
    """Nearest city dict (needs latitude/longitude keys) and its distance km."""
    best, best_d = None, float("inf")
    for c in cities:
        d = haversine_km(lat, lon, float(c["latitude"]), float(c["longitude"]))
        if d < best_d:
            best, best_d = c, d
    return best, best_d


def within_fire_radius(lat1: float, lon1: float, lat2: float, lon2: float) -> bool:
    return haversine_km(lat1, lon1, lat2, lon2) <= FIRE_RADIUS_KM
