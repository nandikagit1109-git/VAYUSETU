"""Hotspot endpoints. Wind fields are computed by joining hotspot location
with the bundled mock wind data AT REQUEST TIME — they are never stored."""
from fastapi import APIRouter
from sqlmodel import select

from ..db import get_session
from ..models import Hotspot
from ..services import mock_data

router = APIRouter(prefix="/api/hotspots", tags=["hotspots"])


@router.get("")
def list_hotspots():
    with get_session() as session:
        hotspots = session.exec(select(Hotspot)).all()
        out = []
        for h in hotspots:
            wind = mock_data.wind_for_location(h.latitude, h.longitude)
            out.append({
                "id": h.id,
                "latitude": h.latitude,
                "longitude": h.longitude,
                "cause": h.cause,
                "confidence": h.confidence,
                "detected_at": h.detected_at.isoformat() if h.detected_at else None,
                "wind_direction_deg": wind["wind_direction_deg"],
                "wind_speed_kmh": wind["wind_speed_kmh"],
                "downwind_city": wind["downwind_city"],
                "eta_hours": wind["eta_hours"],
            })
        return {"hotspots": out}
