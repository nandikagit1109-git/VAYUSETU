"""Citizen report endpoints (section 10, 11.3).

City assignment is server-side: nearest registry city within
REPORT_MAX_DISTANCE_KM. Any client-supplied city field is ignored (none
exists in the schema). Photos are never stored — only their SHA-256 hash.
"""
import base64
import hashlib
import logging
import threading
import time
from collections import deque

from fastapi import APIRouter, Request
from sqlmodel import col, select

from ..config import PHOTO_MAX_BYTES, REPORT_MAX_DISTANCE_KM
from ..db import get_session
from ..errors import error_envelope
from ..geo import haversine_km
from ..schemas import ReportCreate
from ..services import cv_scorer
from ..store import DataStore
from ..tables import CitizenReportRow

logger = logging.getLogger("vayusetu.reports")
router = APIRouter(prefix="/api/reports", tags=["reports"])

INDIA_LAT = (6.5, 37.5)
INDIA_LON = (68.0, 97.5)

# Rate limit: 20 report submissions per minute per client IP, in-memory
# sliding window. Prevents a stuck retry loop from flooding the map (section 12).
# Per-IP deques (not one shared list): checking never scans every client's
# history, and each deque is capped so a chatty client cannot grow memory.
_RATE_LIMIT = 20
_RATE_WINDOW_S = 60.0
_rate_lock = threading.Lock()
_rate_hits: dict[str, deque[float]] = {}
_MAX_TRACKED_IPS = 10_000


def _check_rate_limit(client_ip: str) -> bool:
    now = time.monotonic()
    with _rate_lock:
        hits = _rate_hits.get(client_ip)
        if hits is None:
            if len(_rate_hits) >= _MAX_TRACKED_IPS:
                # Evict fully-expired IPs before refusing new ones.
                stale = [ip for ip, q in _rate_hits.items() if not q or now - q[-1] > _RATE_WINDOW_S]
                for ip in stale:
                    del _rate_hits[ip]
                if len(_rate_hits) >= _MAX_TRACKED_IPS:
                    _rate_hits.clear()  # extreme case: reset rather than grow
            hits = _rate_hits[client_ip] = deque(maxlen=_RATE_LIMIT)
        # Drop entries outside the window (deque is ordered by time).
        while hits and now - hits[0] > _RATE_WINDOW_S:
            hits.popleft()
        if len(hits) >= _RATE_LIMIT:
            # Record nothing on a rejected request: a 429 storm must not
            # extend the client's own ban window.
            return False
        hits.append(now)
        return True


def _trust_weight(haze_score: float, ref_aqi: float | None) -> float:
    if ref_aqi is None:
        return 0.6
    return min(1.0, max(0.2, 1.0 - abs(haze_score - ref_aqi) / 250.0))


@router.post("", status_code=201)
def create_report(body: ReportCreate, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        return error_envelope("too many reports; retry in a minute", status_code=429)

    # Coordinate validation (India bbox).
    if not (INDIA_LAT[0] <= body.latitude <= INDIA_LAT[1]):
        return error_envelope("latitude outside India (6.5-37.5)", status_code=422)
    if not (INDIA_LON[0] <= body.longitude <= INDIA_LON[1]):
        return error_envelope("longitude outside India (68.0-97.5)", status_code=422)
    if body.photo_base64 is None and body.manual_visibility is None:
        return error_envelope("at least one of photo_base64 or manual_visibility is required", status_code=422)

    store = DataStore.instance()

    # Decode + score the photo BEFORE touching the DB.
    photo_raw: bytes | None = None
    if body.photo_base64 is not None:
        try:
            photo_raw = cv_scorer.decode_photo(body.photo_base64, PHOTO_MAX_BYTES)
        except cv_scorer.ImageTooLarge:
            return error_envelope("image too large", status_code=413)
        except cv_scorer.PhotoError:
            return error_envelope("could not read image", status_code=422)

    try:
        haze_score, confidence, scorer = cv_scorer.score_report(photo_raw, body.manual_visibility)
    except cv_scorer.PhotoError:
        return error_envelope("could not read image", status_code=422)

    # Server-side city assignment.
    nearest, dist = None, float("inf")
    for c in store.cities:
        d = haversine_km(body.latitude, body.longitude, c.latitude, c.longitude)
        if d < dist:
            nearest, dist = c, d
    if nearest is None or dist > REPORT_MAX_DISTANCE_KM:
        return error_envelope("outside coverage", status_code=422)

    ref_aqi, _ = store.latest_aqi(nearest.city_id)
    trust = _trust_weight(haze_score, ref_aqi)

    photo_sha = hashlib.sha256(photo_raw).hexdigest() if photo_raw is not None else None
    with get_session() as session:
        report = CitizenReportRow(
            latitude=round(body.latitude, 4),
            longitude=round(body.longitude, 4),
            city_id=nearest.city_id,
            haze_score=round(float(haze_score), 1),
            confidence=round(float(confidence), 4),
            trust_weight=round(float(trust), 4),
            source="user",
            photo_sha256=photo_sha,
        )
        session.add(report)
        session.commit()
        session.refresh(report)
        return {
            "id": report.id,
            "city_id": report.city_id,
            "haze_score": report.haze_score,
            "confidence": report.confidence,
            "trust_weight": report.trust_weight,
            "scorer": scorer,
        }


@router.get("")
def list_reports(city_id: str | None = None):
    with get_session() as session:
        stmt = select(CitizenReportRow)
        if city_id:
            stmt = stmt.where(col(CitizenReportRow.city_id) == city_id)
        rows = session.exec(stmt.order_by(col(CitizenReportRow.created_at).desc())).all()
        return {
            "reports": [
                {
                    "id": r.id,
                    "latitude": r.latitude,
                    "longitude": r.longitude,
                    "city_id": r.city_id,
                    "haze_score": r.haze_score,
                    "confidence": r.confidence,
                    "trust_weight": r.trust_weight,
                    "source": r.source,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows[:500]
            ]
        }
