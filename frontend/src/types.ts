// TypeScript interfaces mirroring the backend API contracts (Section 5) EXACTLY.
// Field names and casing must never drift from the backend models.

export interface CitizenReport {
  id: number
  latitude: number
  longitude: number
  city: string
  haze_score: number
  confidence: number
  trust_weight: number
  created_at: string | null
}

export interface SubmitReportRequest {
  latitude: number
  longitude: number
  city: string
  photo_base64: string | null
  manual_visibility: 'clear' | 'hazy' | 'very_hazy' | null
}

export interface SubmitReportResponse {
  id: number
  haze_score: number
  confidence: number
}

export interface Hotspot {
  id: number
  latitude: number
  longitude: number
  cause: 'stubble_burning' | 'industrial' | 'vehicular' | 'unknown' | string
  confidence: number
  detected_at: string | null
  wind_direction_deg: number
  wind_speed_kmh: number
  downwind_city: string | null
  eta_hours: number | null
}

export interface ForecastPointOut {
  forecast_for: string
  predicted_aqi: number
  lower_bound: number
  upper_bound: number
}

export interface ForecastResponse {
  city?: string
  points?: ForecastPointOut[]
  error?: boolean
  message?: string
}

export type AlertSeverity = 'Moderate' | 'Poor' | 'Very Poor' | 'Severe'

export interface Alert {
  id: number
  city: string
  severity: AlertSeverity | string
  predicted_aqi: number
  grap_action: string
  channel: 'dashboard' | 'sms_simulated' | 'whatsapp_simulated' | string
  created_at: string | null
  acknowledged: boolean
}

export interface FederatedRound {
  round: number
  client_losses: {
    delhi: number
    kanpur: number
    pune: number
  }
  global_loss: number
}

export interface FederatedStatus {
  status: 'idle' | 'running' | 'completed'
  rounds: FederatedRound[]
  started_at: string | null
  completed_at: string | null
}

export interface ApiErrorBody {
  error?: boolean
  message?: string
}
