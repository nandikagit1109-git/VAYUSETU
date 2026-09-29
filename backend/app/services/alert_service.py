"""Alert generation (section 9.2).

POST /api/alerts/check: for each city with a forecast, take the horizon 1-3
point with the highest predicted_aqi; map to severity; insert one only if NO
alert of any state (acknowledged or not) exists for the same city_id +
severity + forecast_date. Deduplicating on un-acknowledged alerts only would
recreate an alert 30 seconds after the user acknowledges it, because the UI
calls this endpoint every 30 s. Idempotent by construction. A threading.Lock
serialises concurrent checks.
"""
import json
import logging
import threading

from sqlmodel import col, select

from ..db import get_session
from ..tables import AlertRow
from .forecast_service import ForecastUnavailable, get_forecast
from .grap_rules import action_for, channels_for

logger = logging.getLogger("vayusetu.alerts")

_check_lock = threading.Lock()

NAME_FALLBACK = "city"


def _severity(aqi: float) -> str | None:
    if 200 < aqi <= 300:
        return "Poor"
    if 300 < aqi <= 400:
        return "Very Poor"
    if aqi > 400:
        return "Severe"
    return None


def check_alerts(store) -> int:
    """Runs the threshold check for every active city; returns created count."""
    created = 0
    with _check_lock:
        for entry in store.active_cities():
            try:
                fc = get_forecast(store, entry.city_id)
            except ForecastUnavailable:
                continue
            except Exception as exc:
                logger.warning("alert check: forecast failed for %s (%s)", entry.city_id, exc)
                continue

            future = [p for p in fc["points"] if p["horizon_days"] in (1, 2, 3)]
            if not future:
                continue
            worst = max(future, key=lambda p: p["predicted_aqi"])
            severity = _severity(worst["predicted_aqi"])
            if severity is None:
                continue

            framework, stage, action = action_for(worst["predicted_aqi"], ncr=entry.ncr == 1)
            channels = channels_for(severity)

            with get_session() as session:
                existing = session.exec(
                    select(AlertRow).where(
                        col(AlertRow.city_id) == entry.city_id,
                        col(AlertRow.severity) == severity,
                        col(AlertRow.forecast_date) == worst["date"],
                    )
                ).first()
                if existing is not None:
                    continue
                session.add(AlertRow(
                    city_id=entry.city_id,
                    severity=severity,
                    predicted_aqi=round(float(worst["predicted_aqi"]), 1),
                    forecast_date=worst["date"],
                    action_framework=framework,
                    grap_stage=stage,
                    action=action,
                    channels_json=json.dumps(channels),
                    acknowledged=False,
                ))
                session.commit()
                created += 1
    return created


def list_alerts() -> list[dict]:
    from ..store import DataStore

    store = DataStore.instance()
    with get_session() as session:
        rows = session.exec(
            select(AlertRow).order_by(col(AlertRow.created_at).desc(), col(AlertRow.id).desc())
        ).all()
        alerts = []
        for a in rows:
            city = store.city(a.city_id)
            alerts.append({
                "id": a.id,
                "city_id": a.city_id,
                "city_name": city.name if city else a.city_id,
                "severity": a.severity,
                "predicted_aqi": a.predicted_aqi,
                "forecast_date": a.forecast_date,
                "action_framework": a.action_framework,
                "grap_stage": a.grap_stage,
                "action": a.action,
                "channels": json.loads(a.channels_json),
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "acknowledged": a.acknowledged,
            })
        return alerts


def acknowledge(alert_id: int) -> bool:
    with get_session() as session:
        alert = session.get(AlertRow, alert_id)
        if alert is None:
            return False
        alert.acknowledged = True
        session.add(alert)
        session.commit()
        return True
