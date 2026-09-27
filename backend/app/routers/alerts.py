"""Alert endpoints, including the periodic threshold check."""
import logging
import threading

from fastapi import APIRouter
from sqlmodel import col, select

from ..db import get_session
from ..models import Alert, utcnow
from ..services import forecast_model
from ..services.grap_rules import grap_action_for_aqi

logger = logging.getLogger("vayusetu.alerts")
router = APIRouter(prefix="/api/alerts", tags=["alerts"])

GRAP_THRESHOLD_AQI = 200.0  # GRAP Stage-I invokes above AQI 200

# Serialises concurrent /check calls (the UI fires one on load and every 30s;
# without this, two simultaneous checks can both see "no un-acknowledged
# alert" and create duplicates).
_check_lock = threading.Lock()


def _alert_dict(a: Alert) -> dict:
    return {
        "id": a.id,
        "city": a.city,
        "severity": a.severity,
        "predicted_aqi": a.predicted_aqi,
        "grap_action": a.grap_action,
        "channel": a.channel,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "acknowledged": a.acknowledged,
    }


@router.get("")
def list_alerts():
    with get_session() as session:
        alerts = session.exec(
            select(Alert).order_by(col(Alert.created_at).desc(), col(Alert.id).desc())
        ).all()
        return {"alerts": [_alert_dict(a) for a in alerts]}


@router.post("/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: int):
    with get_session() as session:
        alert = session.get(Alert, alert_id)
        if alert is None:
            return {"error": True, "message": f"alert {alert_id} not found"}
        alert.acknowledged = True
        session.add(alert)
        session.commit()
        return {"id": alert.id, "acknowledged": True}


@router.post("/check")
def check_alerts():
    """Reads the latest forecast for all 3 cities; if any point in the next
    24h crosses a GRAP threshold and no un-acknowledged alert exists for that
    city+severity, creates new Alert rows. Called on load + every 30s."""
    created = 0
    with _check_lock:
        try:
            for city in ("delhi", "kanpur", "pune"):
                try:
                    fc = forecast_model.get_forecast(city)
                except Exception as exc:
                    logger.warning("alert check: no forecast for %s (%s)", city, exc)
                    continue

                raw_points = fc["raw_points"]
                if not raw_points:
                    continue
                base = raw_points[0]["forecast_for"]
                window = [p for p in raw_points if (p["forecast_for"] - base).total_seconds() <= 24 * 3600]
                max_aqi = max(p["predicted_aqi"] for p in window)
                if max_aqi <= GRAP_THRESHOLD_AQI:
                    continue
                severity, action = grap_action_for_aqi(max_aqi)

                with get_session() as session:
                    existing = session.exec(
                        select(Alert).where(
                            col(Alert.city) == city,
                            col(Alert.severity) == severity,
                            col(Alert.acknowledged) == False,  # noqa: E712
                        )
                    ).first()
                    if existing is not None:
                        continue
                    session.add(Alert(
                        city=city,
                        severity=severity,
                        predicted_aqi=round(max_aqi, 1),
                        grap_action=action,
                        channel="dashboard",
                        created_at=utcnow(),
                        acknowledged=False,
                    ))
                    session.commit()
                    created += 1
        except Exception as exc:
            logger.warning("alert check failed: %s", exc)
    return {"created": created}
