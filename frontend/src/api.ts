// One typed function per backend endpoint (section 11.3). All requests go
// through relative /api/... URLs (Vite proxies them to the backend). Every
// failure path throws an Error carrying the envelope's message, so callers
// always render a specific string, never a stack trace.
import type {
  Alert,
  ApiError,
  City,
  CityHistoryPoint,
  CitizenReport,
  FlEval,
  FlStatus,
  Forecast,
  Hotspot,
  Meta,
  PointAqi,
  ReportCreate,
  ReportResult,
} from './types'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    })
  } catch {
    throw new Error('Cannot reach the backend. Is the API server running?')
  }
  let body: unknown = null
  try {
    body = await res.json()
  } catch {
    // Non-JSON body: fall through to the status check below.
  }
  if (!res.ok) {
    const err = body as Partial<ApiError> | null
    throw new Error(err?.message ?? `HTTP ${res.status}`)
  }
  return body as T
}

export function getMeta(): Promise<Meta> {
  return request<Meta>('/api/meta')
}

export function getCities(): Promise<{ cities: City[] }> {
  return request<{ cities: City[] }>('/api/cities')
}

export function getCityHistory(cityId: string, days = 30): Promise<{ city_id: string; points: CityHistoryPoint[] }> {
  return request(`/api/cities/${encodeURIComponent(cityId)}/history?days=${days}`)
}

export function submitReport(body: ReportCreate): Promise<ReportResult> {
  return request<ReportResult>('/api/reports', { method: 'POST', body: JSON.stringify(body) })
}

export function getReports(cityId?: string): Promise<{ reports: CitizenReport[] }> {
  const qs = cityId ? `?city_id=${encodeURIComponent(cityId)}` : ''
  return request(`/api/reports${qs}`)
}

export function getHotspots(): Promise<{ hotspots: Hotspot[] }> {
  return request('/api/hotspots')
}

// Point AQI (section 7b): "outside India" arrives as HTTP 200 + the error
// envelope, so the promise resolves and the caller renders the message.
export function getPointAqi(latitude: number, longitude: number): Promise<PointAqi | ApiError> {
  return request(`/api/aqi?latitude=${latitude}&longitude=${longitude}`)
}

// Expected "not available" states arrive as HTTP 200 + the error envelope, so
// the promise resolves; callers check `error` and render a pending state.
export function getForecast(cityId: string): Promise<Forecast | ApiError> {
  return request(`/api/forecast?city_id=${encodeURIComponent(cityId)}`)
}

export function getAlerts(): Promise<{ alerts: Alert[] }> {
  return request('/api/alerts')
}

export function checkAlerts(): Promise<{ created: number }> {
  return request('/api/alerts/check', { method: 'POST' })
}

export function acknowledgeAlert(id: number): Promise<{ id: number; acknowledged: true }> {
  return request(`/api/alerts/${id}/acknowledge`, { method: 'POST' })
}

export function getFederatedStatus(): Promise<FlStatus> {
  return request('/api/federated/status')
}

export function runFederated(): Promise<{ message: string }> {
  return request('/api/federated/run', { method: 'POST' })
}

export function getFederatedEval(): Promise<FlEval> {
  return request('/api/federated/eval')
}
