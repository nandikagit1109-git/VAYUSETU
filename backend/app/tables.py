"""SQLModel tables — only the two tables allowed by section 11.1.

SQLite connections are thread-bound, so every request and every background
thread opens its own session via app.db.get_session (engine is created with
check_same_thread=False and sessions never cross threads).
"""
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    # Timezone-aware on purpose (section 12 forbids datetime.utcnow()).
    return datetime.now(timezone.utc)


class CitizenReportRow(SQLModel, table=True):
    __tablename__ = "citizen_report"

    id: Optional[int] = Field(default=None, primary_key=True)
    latitude: float
    longitude: float
    city_id: str
    haze_score: float
    confidence: float
    trust_weight: float
    source: str  # "user" | "seed"
    photo_sha256: Optional[str] = None  # hash only — the photo itself is never stored
    created_at: datetime = Field(default_factory=utcnow)


class AlertRow(SQLModel, table=True):
    __tablename__ = "alert"

    id: Optional[int] = Field(default=None, primary_key=True)
    city_id: str
    severity: str  # "Poor" | "Very Poor" | "Severe"
    predicted_aqi: float
    forecast_date: str  # plain YYYY-MM-DD
    action_framework: str  # "GRAP" | "ADVISORY"
    grap_stage: Optional[str] = None
    action: str
    channels_json: str  # JSON-encoded list of channel strings
    created_at: datetime = Field(default_factory=utcnow)
    acknowledged: bool = Field(default=False)
