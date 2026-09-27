"""SQLModel table definitions + request schemas (Section 5.1 of the spec)."""
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CitizenReport(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    latitude: float
    longitude: float
    city: str
    photo_filename: Optional[str] = None
    haze_score: float  # 0-500 AQI-proxy scale
    confidence: float  # 0-1
    trust_weight: float = Field(default=1.0)  # 0-1
    created_at: datetime = Field(default_factory=utcnow)


class Hotspot(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    latitude: float
    longitude: float
    cause: str  # "stubble_burning" | "industrial" | "vehicular" | "unknown"
    confidence: float  # 0-1
    detected_at: datetime


class ForecastPoint(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    city: str
    forecast_for: datetime
    predicted_aqi: float
    lower_bound: float
    upper_bound: float
    generated_at: datetime


class Alert(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    city: str
    severity: str  # "Moderate"|"Poor"|"Very Poor"|"Severe"
    predicted_aqi: float
    grap_action: str
    channel: str  # "dashboard" | "sms_simulated" | "whatsapp_simulated"
    created_at: datetime = Field(default_factory=utcnow)
    acknowledged: bool = Field(default=False)


class ReportCreate(BaseModel):
    latitude: float
    longitude: float
    city: str
    photo_base64: Optional[str] = None
    manual_visibility: Optional[str] = None  # "clear"|"hazy"|"very_hazy"
