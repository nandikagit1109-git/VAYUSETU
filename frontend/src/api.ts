// One typed function per backend endpoint. All requests go through /api
// (proxied to the backend by Vite in dev, and by docker-compose in Docker).
import type {
  Alert,
  ApiErrorBody,
  CitizenReport,
  FederatedStatus,
  ForecastResponse,
  Hotspot,
  SubmitReportRequest,
  SubmitReportResponse,
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
  if (!res.ok) {
    let message = `HTTP ${res.status}`
    try {
      const body = (await res.json()) as ApiErrorBody
      if (body.message) message = body.message
    } catch {
      // non-JSON error body: keep the HTTP status message
    }
    throw new Error(message)
  }
  return (await res.json()) as T
}

export function submitReport(body: SubmitReportRequest): Promise<SubmitReportResponse> {
  return request<SubmitReportResponse>('/api/reports', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function getReports(city?: string): Promise<{ reports: CitizenReport[] }> {
  const qs = city ? `?city=${encodeURIComponent(city)}` : ''
  return request<{ reports: CitizenReport[] }>(`/api/reports${qs}`)
}

export function getHotspots(): Promise<{ hotspots: Hotspot[] }> {
  return request<{ hotspots: Hotspot[] }>('/api/hotspots')
}

export function getForecast(city: string): Promise<ForecastResponse> {
  return request<ForecastResponse>(`/api/forecast?city=${encodeURIComponent(city)}`)
}

export function getAlerts(): Promise<{ alerts: Alert[] }> {
  return request<{ alerts: Alert[] }>('/api/alerts')
}

export function acknowledgeAlert(id: number): Promise<{ id: number; acknowledged: boolean }> {
  return request<{ id: number; acknowledged: boolean }>(`/api/alerts/${id}/acknowledge`, {
    method: 'POST',
  })
}

export function checkAlerts(): Promise<{ created: number }> {
  return request<{ created: number }>('/api/alerts/check', { method: 'POST' })
}

export function getFederatedStatus(): Promise<FederatedStatus> {
  return request<FederatedStatus>('/api/federated/status')
}

export function runFederated(): Promise<{ message: string }> {
  return request<{ message: string }>('/api/federated/run', { method: 'POST' })
}
