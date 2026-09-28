"""Alert endpoints (section 11.3)."""
from fastapi import APIRouter

from ..errors import error_envelope
from ..services import alert_service
from ..store import DataStore

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("")
def list_alerts():
    return {"alerts": alert_service.list_alerts()}


@router.post("/check")
def check_alerts():
    store = DataStore.instance()
    created = alert_service.check_alerts(store)
    return {"created": created}


@router.post("/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: int):
    ok = alert_service.acknowledge(alert_id)
    if not ok:
        return error_envelope(f"alert {alert_id} not found", status_code=404)
    return {"id": alert_id, "acknowledged": True}
