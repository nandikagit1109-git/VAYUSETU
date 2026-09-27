"""Citizen report endpoints."""
import base64
import logging
import uuid

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlmodel import col, select

from ..config import UPLOAD_DIR
from ..db import get_session
from ..models import CitizenReport, ReportCreate, utcnow
from ..services import cv_model

logger = logging.getLogger("vayusetu.reports")
router = APIRouter(prefix="/api/reports", tags=["reports"])


def _save_photo(photo_base64: str) -> str | None:
    """Persist the uploaded photo; failure is non-fatal (filename stays None)."""
    try:
        payload = photo_base64
        if "," in payload and payload.strip().lower().startswith("data:"):
            payload = payload.split(",", 1)[1]
        raw = base64.b64decode(payload)
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"report_{uuid.uuid4().hex}.jpg"
        with open(UPLOAD_DIR / filename, "wb") as f:
            f.write(raw)
        return filename
    except Exception as exc:
        logger.warning("could not save uploaded photo: %s", exc)
        return None


@router.post("", status_code=201)
def create_report(body: ReportCreate):
    if body.photo_base64 is None and body.manual_visibility is None:
        return JSONResponse(
            status_code=400,
            content={"error": True, "message": "at least one of photo_base64 or manual_visibility is required"},
        )
    if body.manual_visibility is not None and body.manual_visibility not in ("clear", "hazy", "very_hazy"):
        return JSONResponse(
            status_code=400,
            content={"error": True, "message": "manual_visibility must be 'clear', 'hazy' or 'very_hazy'"},
        )

    haze_score, confidence = cv_model.score_report(body.photo_base64, body.manual_visibility)
    photo_filename = _save_photo(body.photo_base64) if body.photo_base64 else None

    with get_session() as session:
        report = CitizenReport(
            latitude=body.latitude,
            longitude=body.longitude,
            city=body.city.strip().lower(),
            photo_filename=photo_filename,
            haze_score=haze_score,
            confidence=confidence,
            trust_weight=1.0,
            created_at=utcnow(),
        )
        session.add(report)
        session.commit()
        session.refresh(report)
        return {"id": report.id, "haze_score": report.haze_score, "confidence": report.confidence}


@router.get("")
def list_reports(city: str | None = None):
    with get_session() as session:
        stmt = select(CitizenReport)
        if city:
            stmt = stmt.where(col(CitizenReport.city) == city.strip().lower())
        reports = session.exec(stmt.order_by(col(CitizenReport.created_at).desc())).all()
        return {
            "reports": [
                {
                    "id": r.id,
                    "latitude": r.latitude,
                    "longitude": r.longitude,
                    "city": r.city,
                    "haze_score": r.haze_score,
                    "confidence": r.confidence,
                    "trust_weight": r.trust_weight,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in reports
            ]
        }
