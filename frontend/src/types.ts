// TypeScript interfaces mirroring the backend Pydantic models (section 11.2)
// VERBATIM. Field names and casing must never drift from the backend.

export type Tier = 1 | 2 | 3;
export type ApiError = { error: true; message: string; details?: unknown };

export interface Meta {
  data_mode: "synthetic" | "real";
  fallback_reason: string | null;
  demo_now: string;            // YYYY-MM-DD
  n_cities: number; n_tier1: number; n_tier2: number; n_tier3: number;
  model_version: string | null;
  model_method: "federated_gru" | "persistence";
  sources: string[];           // human-readable data provenance
  fl_status: "idle" | "running" | "completed" | "failed";
}
export interface City {
  city_id: string; name: string; state: string;
  latitude: number; longitude: number; tier: Tier;
  latest_aqi: number | null; latest_date: string | null;
  citizen_adjusted_aqi: number | null; report_count_24h: number;
}
export interface CityHistoryPoint { date: string; aqi: number | null; pm25: number | null; }
export interface CitizenReport {
  id: number; latitude: number; longitude: number; city_id: string;
  haze_score: number; confidence: number; trust_weight: number;
  source: "user" | "seed"; created_at: string;   // ISO-8601 UTC
}
export interface ReportCreate {
  latitude: number; longitude: number;
  photo_base64?: string | null;
  manual_visibility?: "clear" | "hazy" | "very_hazy" | null;
}
export interface ReportResult { id: number; city_id: string; haze_score: number; confidence: number; trust_weight: number; scorer: "heuristic_v1" | "manual"; }
export interface Hotspot {
  id: string; latitude: number; longitude: number;
  cause: "stubble_burning" | "open_burning" | "industrial";
  confidence: number; detected_on: string; frp: number | null;
  wind_direction_deg: number | null; wind_speed_ms: number | null; wind_toward_deg: number | null;
  downwind_city_id: string | null; downwind_city_name: string | null;
  distance_km: number | null; eta_hours: number | null;
}
export interface ForecastPoint {
  date: string; horizon_days: 0 | 1 | 2 | 3;
  predicted_aqi: number; lower_bound: number; upper_bound: number; observed: boolean;
}
export interface Forecast {
  city_id: string; tier: Tier;
  method: "federated_gru" | "persistence" | "neighbor_idw";
  model_version: string | null; points: ForecastPoint[];
}
export interface PointAqiContributor { city_id: string; name: string; distance_km: number; weight: number; latest_aqi: number; }
export interface PointAqi {
  latitude: number; longitude: number;
  estimated_aqi: number; category: string;
  method: "idw_point_interpolation";
  confidence: number;                 // 0-1
  as_of: string;                       // date of the underlying ground data
  nearest_city_id: string; nearest_city_name: string; nearest_city_distance_km: number;
  contributing_cities: PointAqiContributor[];
  nearby_reports_considered: number;
}
export interface Alert {
  id: number; city_id: string; city_name: string;
  severity: "Poor" | "Very Poor" | "Severe";
  predicted_aqi: number; forecast_date: string;
  action_framework: "GRAP" | "ADVISORY"; grap_stage: string | null; action: string;
  channels: ("dashboard" | "sms_simulated")[]; created_at: string; acknowledged: boolean;
}
export interface FlRound { round: number; client_losses: Record<string, number>; global_loss: number; global_val_mae: number; }
export interface FlStatus {
  status: "idle" | "running" | "completed" | "failed";
  rounds: FlRound[]; total_rounds: number;
  clients: string[]; excluded: { city_id: string; reason: string }[];
  started_at: string | null; completed_at: string | null; error: string | null;
}
export interface FlEvalRow { city_id: string; name: string; n_val: number; mae_persistence: number; mae_local: number; mae_federated: number; mae_personalized: number; }
export interface FlEval {
  available: boolean; rows: FlEvalRow[];
  mean_mae_persistence: number | null; mean_mae_local: number | null; mean_mae_federated: number | null; mean_mae_personalized: number | null;
}
