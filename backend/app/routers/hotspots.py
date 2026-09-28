"""/api/hotspots (section 11.3)."""
from fastapi import APIRouter

from ..services.hotspot_service import get_hotspots
from ..store import DataStore

router = APIRouter(prefix="/api/hotspots", tags=["hotspots"])


@router.get("")
def list_hotspots():
    store = DataStore.instance()
    return {"hotspots": get_hotspots(store)}
