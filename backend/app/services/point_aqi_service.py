"""Point AQI (section 7b): best-effort estimate for ANY lat/lon in India.

Distinct from GET /api/forecast (which takes a city_id). This answers "what is
the air quality right here" for an arbitrary coordinate — a village, a highway,
a farm — not just the 28 registry cities.

Rules:
- Outside the India bbox is an expected "not available" case: the router
  returns a 200 envelope, never a 4xx/5xx for a valid-but-outside query.
- Source cities are tier 1 only — chaining interpolation on interpolation
  (tier-2 values are themselves interpolated) would compound error.
- K = 6 nearest tier-1 cities, weight w = 1 / max(d_km, 10)^2, no distance cap,
  so the far Northeast or the Thar still gets a number, flagged low-confidence.
- Recent citizen reports within 50 km blend in exactly like the per-city
  adjusted AQI: (3*base + sum(trust*score)) / (3 + sum(trust)).
- confidence = clip(1 - nearest_km/300, 0.15, 0.95).
- Target round-trip: well under 200 ms — this is the same lightweight IDW math
  as tier-2/3 forecasting, centred on an arbitrary point.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from sqlmodel import col, select

from ..db import get_session
from ..geo import haversine_km
from ..services.aqi import category
from ..tables import CitizenReportRow

K_NEAREST = 6
REPORT_RADIUS_KM = 50.0

INDIA_LAT = (6.5, 37.5)
INDIA_LON = (68.0, 97.5)


def outside_india(latitude: float, longitude: float) -> bool:
    return not (INDIA_LAT[0] <= latitude <= INDIA_LAT[1]) or not (
        INDIA_LON[0] <= longitude <= INDIA_LON[1]
    )


def _tier1_with_aqi(store) -> list[tuple[object, float, str]]:
    """Active tier-1 cities that have a latest AQI, with value + date."""
    out = []
    for c in store.active_cities():
        if store.tier_of(c.city_id) != 1:
            continue
        aqi, as_of = store.latest_aqi(c.city_id)
        if aqi is None:
            continue
        out.append((c, float(aqi), as_of or store.demo_now or ""))
    return out


def estimate_point_aqi(store, latitude: float, longitude: float) -> dict:
    tier1 = _tier1_with_aqi(store)
    if not tier1:
        raise LookupError("no monitored city has ground AQI yet")

    # Distance-sorted tier-1 cities (sort before slicing so the result does not
    # depend on how cities.csv happens to be sorted — trap 9 of test_point_aqi).
    scored = sorted(
        ((c, aqi, as_of, haversine_km(latitude, longitude, c.latitude, c.longitude)) for c, aqi, as_of in tier1),
        key=lambda t: t[3],
    )
    nearest = scored[:K_NEAREST]

    contributors = []
    wsum = 0.0
    weighted = 0.0
    for c, aqi, as_of, d in nearest:
        w = 1.0 / max(d, 10.0) ** 2
        wsum += w
        weighted += w * aqi
        contributors.append({
            "city_id": c.city_id,
            "name": c.name,
            "distance_km": round(d, 1),
            "weight": round(w, 6),
            "latest_aqi": round(aqi, 1),
        })
    base = weighted / wsum if wsum > 0 else scored[0][1]
    as_of = max(as_of for _c, _a, as_of, _d in nearest)

    # Fold in recent citizen reports within 50 km (same blend as per-city AQI).
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    total_trust = 0.0
    weighted_score = 0.0
    nearby_reports = 0
    try:
        with get_session() as session:
            rows = session.exec(
                select(CitizenReportRow)
                .where(col(CitizenReportRow.created_at) >= cutoff)
            ).all()
    except Exception:
        rows = []
    for r in rows:
        d = haversine_km(latitude, longitude, r.latitude, r.longitude)
        if d > REPORT_RADIUS_KM:
            continue
        total_trust += r.trust_weight
        weighted_score += r.trust_weight * r.haze_score
        nearby_reports += 1
    if nearby_reports > 0 and total_trust > 0:
        estimated = (3.0 * base + weighted_score) / (3.0 + total_trust)
    else:
        estimated = base

    nearest_km = scored[0][3]
    confidence = min(0.95, max(0.15, 1.0 - nearest_km / 300.0))

    return {
        "latitude": round(float(latitude), 4),
        "longitude": round(float(longitude), 4),
        "estimated_aqi": round(min(500.0, max(0.0, estimated)), 1),
        "category": category(estimated),
        "method": "idw_point_interpolation",
        "confidence": round(confidence, 4),
        "as_of": as_of,
        "nearest_city_id": scored[0][0].city_id,
        "nearest_city_name": scored[0][0].name,
        "nearest_city_distance_km": round(nearest_km, 1),
        "contributing_cities": contributors,
        "nearby_reports_considered": nearby_reports,
    }
