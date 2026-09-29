import { describe, expect, it } from 'vitest'
import type {
  Alert, City, CityHistoryPoint, CitizenReport, FlEval, FlStatus, Forecast,
  Hotspot, Meta, PointAqi, ReportResult,
} from '../types'

// Frontend test 2 (section 14): assign a fixture of every endpoint's example
// JSON to its interface. Any field rename on either side breaks compilation.

const meta: Meta = {
  data_mode: 'synthetic', fallback_reason: null, demo_now: '2025-11-10',
  n_cities: 28, n_tier1: 20, n_tier2: 5, n_tier3: 3,
  model_version: 'fedavg-20251110T000000Z', model_method: 'federated_gru',
  sources: ['Synthetic generator (seed 42)'], fl_status: 'completed',
}
const city: City = {
  city_id: 'delhi', name: 'Delhi', state: 'Delhi', latitude: 28.6139, longitude: 77.209,
  tier: 1, latest_aqi: 355.2, latest_date: '2025-11-10',
  citizen_adjusted_aqi: 350.0, report_count_24h: 2,
}
const historyPoint: CityHistoryPoint = { date: '2025-11-10', aqi: 355.2, pm25: 210.5 }
const report: CitizenReport = {
  id: 1, latitude: 28.6, longitude: 77.2, city_id: 'delhi', haze_score: 300,
  confidence: 0.4, trust_weight: 0.78, source: 'user', created_at: '2025-11-10T00:00:00+00:00',
}
const reportResult: ReportResult = {
  id: 1, city_id: 'delhi', haze_score: 300, confidence: 0.4,
  trust_weight: 0.78, scorer: 'heuristic_v1',
}
const hotspot: Hotspot = {
  id: 'fire-2025-11-09-0', latitude: 30.5, longitude: 75.5,
  cause: 'stubble_burning', confidence: 0.9, detected_on: '2025-11-09', frp: 42.5,
  wind_direction_deg: 315.0, wind_speed_ms: 2.4, wind_toward_deg: 135.0,
  downwind_city_id: 'ludhiana', downwind_city_name: 'Ludhiana',
  distance_km: 88.0, eta_hours: 10.2,
}
const forecast: Forecast = {
  city_id: 'varanasi', tier: 2, method: 'neighbor_idw', model_version: null,
  points: [{ date: '2025-11-11', horizon_days: 1, predicted_aqi: 300, lower_bound: 250, upper_bound: 350, observed: false }],
}
const pointAqi: PointAqi = {
  latitude: 27.0, longitude: 70.5, estimated_aqi: 200.0, category: 'Poor',
  method: 'idw_point_interpolation', confidence: 0.3, as_of: '2025-11-10',
  nearest_city_id: 'jaipur', nearest_city_name: 'Jaipur', nearest_city_distance_km: 320.0,
  contributing_cities: [], nearby_reports_considered: 0,
}
const alert: Alert = {
  id: 7, city_id: 'delhi', city_name: 'Delhi', severity: 'Very Poor',
  predicted_aqi: 360.0, forecast_date: '2025-11-11', action_framework: 'GRAP',
  grap_stage: 'Stage II', action: 'All Stage I actions, plus restrict diesel generator use',
  channels: ['dashboard', 'sms_simulated'], created_at: '2025-11-10T00:00:00+00:00',
  acknowledged: false,
}
const flStatus: FlStatus = {
  status: 'completed', rounds: [{ round: 1, client_losses: { delhi: 0.02 }, global_loss: 0.02, global_val_mae: 37.1 }],
  total_rounds: 8, clients: ['delhi'], excluded: [{ city_id: 'kochi', reason: 'only 41 training windows' }],
  started_at: null, completed_at: null, error: null,
}
const flEval: FlEval = {
  available: true,
  rows: [{ city_id: 'delhi', name: 'Delhi', n_val: 40, mae_persistence: 28.3, mae_local: 40.0, mae_federated: 68.9, mae_personalized: 39.2 }],
  mean_mae_persistence: 21.1, mean_mae_local: 25.4, mean_mae_federated: 37.1, mean_mae_personalized: 24.2,
}

describe('contract fixtures assign to types.ts interfaces', () => {
  it('every endpoint fixture is assignable', () => {
    expect(meta.n_cities).toBe(28)
    expect(city.tier).toBe(1)
    expect(historyPoint.aqi).not.toBeNull()
    expect(report.source).toBe('user')
    expect(reportResult.scorer).toBe('heuristic_v1')
    expect(hotspot.downwind_city_id).toBe('ludhiana')
    expect(forecast.method).toBe('neighbor_idw')
    expect(pointAqi.method).toBe('idw_point_interpolation')
    expect(alert.grap_stage).toBe('Stage II')
    expect(flStatus.rounds.length).toBe(1)
    expect(flEval.available).toBe(true)
  })
})
