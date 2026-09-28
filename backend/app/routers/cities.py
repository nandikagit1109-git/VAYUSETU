"""City endpoints (section 11.3): list and history."""
import math
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query
from sqlmodel import col, select

from ..db import get_session
from ..errors import error_envelope
from ..geo import haversine_km
from ..store import DataStore
from ..tables import CitizenReportRow

router = APIRouter(prefix="/api/cities", tags=["cities"])


def _citizen_adjusted(store, city_id: str, ground_aqi: float | None) -> tuple[float | None, int]:
    """(3*ground + sum(trust_i*score_i)) / (3 + sum(trust_i)) over reports
    created in the last 24 real hours (the only place wall-clock time is used)."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    total_trust = 0.0
    weighted = 0.0
    count = 0
    with get_session() as session:
        rows = session.exec(
            select(CitizenReportRow).where(col(CitizenReportRow.city_id) == city_id)
        ).all()
    for r in rows:
        created = r.created_at
        if created is None:
            continue
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if created < cutoff:
            continue
        total_trust += r.trust_weight
        weighted += r.trust_weight * r.haze_score
        count += 1

    if count == 0:
        return ground_aqi, 0
    if ground_aqi is None:
        # No ground truth: the weighted citizen mean stands alone (section 10).
        denom = total_trust
        value = weighted / denom if denom > 0 else None
        return (round(value, 1) if value is not None else None), count
    value = (3.0 * ground_aqi + weighted) / (3.0 + total_trust)
    return round(value, 1), count


@router.get("")
def list_cities():
    store = DataStore.instance()
    cities_out = []
    for c in store.active_cities():
        latest_aqi, latest_date = store.latest_aqi(c.city_id)
        adjusted, report_count = _citizen_adjusted(store, c.city_id, latest_aqi)
        cities_out.append({
            "city_id": c.city_id,
            "name": c.name,
            "state": c.state,
            "latitude": round(c.latitude, 4),
            "longitude": round(c.longitude, 4),
            "tier": store.tier_of(c.city_id),
            "latest_aqi": None if latest_aqi is None else round(latest_aqi, 1),
            "latest_date": latest_date,
            "citizen_adjusted_aqi": adjusted,
            "report_count_24h": report_count,
        })
    cities_out.sort(key=lambda x: x["name"])
    return {"cities": cities_out}


@router.get("/{city_id}/history")
def city_history(city_id: str, days: int = Query(default=30, ge=1, le=365)):
    store = DataStore.instance()
    if store.city(city_id) is None or city_id not in store.active_ids:
        return error_envelope(f"unknown city {city_id}", status_code=404)
    points = store.history(city_id, days)
    return {"city_id": city_id, "points": points}
