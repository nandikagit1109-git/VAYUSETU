"""Startup seeding: hotspots from the bundled mock satellite data and one
pre-seeded alert so the Alerts tab is never empty."""
import logging
from datetime import datetime, timezone

from sqlmodel import select

from ..models import Alert, Hotspot
from . import mock_data
from .grap_rules import grap_action_for_aqi

logger = logging.getLogger("vayusetu.seed")


def _parse_dt(value, fallback):
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return fallback


def seed_all(session) -> None:
    """Idempotent: alerts seed only into an empty table, hotspots are matched by
    position so widening the mock dataset adds the new sources without touching
    the rows (or the citizen reports pinned near them) that already exist."""
    existing = session.exec(select(Hotspot)).all()
    seen = {(round(h.latitude, 4), round(h.longitude, 4)) for h in existing}
    added = 0
    now = datetime.now(timezone.utc)
    for h in mock_data.get_fire_hotspots():
        try:
            lat = float(h["latitude"])
            lon = float(h["longitude"])
        except Exception as exc:
            logger.warning("skipping malformed hotspot entry %r: %s", h, exc)
            continue
        if (round(lat, 4), round(lon, 4)) in seen:
            continue
        try:
            session.add(Hotspot(
                latitude=lat,
                longitude=lon,
                cause=str(h.get("cause", "unknown")),
                confidence=float(h.get("confidence", 0.5)),
                detected_at=_parse_dt(h.get("detected_at"), now),
            ))
            added += 1
        except Exception as exc:
            logger.warning("skipping malformed hotspot entry %r: %s", h, exc)
    if added:
        session.commit()
        logger.info("seeded %d hotspots from mock satellite data", added)

    existing_alerts = session.exec(select(Alert)).first()
    if existing_alerts is None:
        severity, action = grap_action_for_aqi(312.0)
        session.add(Alert(
            city="delhi",
            severity=severity,
            predicted_aqi=312.0,
            grap_action=action,
            channel="dashboard",
            acknowledged=False,
        ))
        session.commit()
        logger.info("seeded pre-existing alert for delhi")
