"""Pydantic response models mirroring the TypeScript interfaces in section 11.2.

Field names, types and casing are copied 1:1 from the spec. Do not rename,
re-case or reshape anything here without updating frontend/src/types.ts.
"""
from typing import List, Literal, Optional

from pydantic import BaseModel


class Meta(BaseModel):
    data_mode: Literal["synthetic", "real"]
    fallback_reason: Optional[str] = None
    demo_now: str
    n_cities: int
    n_tier1: int
    n_tier2: int
    n_tier3: int
    model_version: Optional[str] = None
    model_method: Literal["federated_gru", "persistence"]
    sources: List[str] = []
    fl_status: Literal["idle", "running", "completed", "failed"]


class City(BaseModel):
    city_id: str
    name: str
    state: str
    latitude: float
    longitude: float
    tier: int
    latest_aqi: Optional[float] = None
    latest_date: Optional[str] = None
    citizen_adjusted_aqi: Optional[float] = None
    report_count_24h: int


class CityHistoryPoint(BaseModel):
    date: str
    aqi: Optional[float] = None
    pm25: Optional[float] = None


class CitizenReport(BaseModel):
    id: int
    latitude: float
    longitude: float
    city_id: str
    haze_score: float
    confidence: float
    trust_weight: float
    source: Literal["user", "seed"]
    created_at: str


class ReportCreate(BaseModel):
    latitude: float
    longitude: float
    photo_base64: Optional[str] = None
    manual_visibility: Optional[Literal["clear", "hazy", "very_hazy"]] = None


class ReportResult(BaseModel):
    id: int
    city_id: str
    haze_score: float
    confidence: float
    trust_weight: float
    scorer: Literal["heuristic_v1", "manual"]


class Hotspot(BaseModel):
    id: str
    latitude: float
    longitude: float
    cause: Literal["stubble_burning", "open_burning", "industrial"]
    confidence: float
    detected_on: str
    frp: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    wind_speed_ms: Optional[float] = None
    wind_toward_deg: Optional[float] = None
    downwind_city_id: Optional[str] = None
    downwind_city_name: Optional[str] = None
    distance_km: Optional[float] = None
    eta_hours: Optional[float] = None


class ForecastPoint(BaseModel):
    date: str
    horizon_days: int  # 0 | 1 | 2 | 3
    predicted_aqi: float
    lower_bound: float
    upper_bound: float
    observed: bool


class Forecast(BaseModel):
    city_id: str
    tier: int
    method: Literal["federated_gru", "persistence", "neighbor_idw"]
    model_version: Optional[str] = None
    points: List[ForecastPoint]


class PointAqiContributor(BaseModel):
    city_id: str
    name: str
    distance_km: float
    weight: float
    latest_aqi: float


class PointAqi(BaseModel):
    latitude: float
    longitude: float
    estimated_aqi: float
    category: str
    method: Literal["idw_point_interpolation"]
    confidence: float
    as_of: str
    nearest_city_id: str
    nearest_city_name: str
    nearest_city_distance_km: float
    contributing_cities: List[PointAqiContributor]
    nearby_reports_considered: int


class Alert(BaseModel):
    id: int
    city_id: str
    city_name: str
    severity: Literal["Poor", "Very Poor", "Severe"]
    predicted_aqi: float
    forecast_date: str
    action_framework: Literal["GRAP", "ADVISORY"]
    grap_stage: Optional[str] = None
    action: str
    channels: List[Literal["dashboard", "sms_simulated"]]
    created_at: str
    acknowledged: bool


class FlRound(BaseModel):
    round: int
    client_losses: dict[str, float]
    global_loss: float
    global_val_mae: float


class FlStatus(BaseModel):
    status: Literal["idle", "running", "completed", "failed"]
    rounds: List[FlRound]
    total_rounds: int
    clients: List[str]
    excluded: List[dict]
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


class FlEvalRow(BaseModel):
    city_id: str
    name: str
    n_val: int
    mae_persistence: float
    mae_local: float
    mae_federated: float
    mae_personalized: float


class FlEval(BaseModel):
    available: bool
    rows: List[FlEvalRow]
    mean_mae_persistence: Optional[float] = None
    mean_mae_local: Optional[float] = None
    mean_mae_federated: Optional[float] = None
    mean_mae_personalized: Optional[float] = None
