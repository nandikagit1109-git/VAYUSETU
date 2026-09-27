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
    """Idempotent: only seeds tables that are empty."""
    existing_hotspots = session.exec(select(Hotspot)).first()
    if existing_hotspots is None:
        now = datetime.now(timezone.utc)
        for h in mock_data.get_fire_hotspots():
            try:
                session.add(Hotspot(
                    latitude=float(h["latitude"]),
                    longitude=float(h["longitude"]),
                    cause=str(h.get("cause", "unknown")),
                    confidence=float(h.get("confidence", 0.5)),
                    detected_at=_parse_dt(h.get("detected_at"), now),
                ))
            except Exception as exc:
                logger.warning("skipping malformed hotspot entry %r: %s", h, exc)
        session.commit()
        logger.info("seeded hotspots from mock satellite data")

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
