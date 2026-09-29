import { afterEach, describe, expect, it, vi } from 'vitest'
import { getPointAqi } from '../api'
import type { PointAqi } from '../types'

// api.ts must resolve with a typed value on success, and reject with an Error
// carrying the envelope message on {error:true} bodies and network failures —
// never an unhandled rejection (section 14, frontend test 1).

const pointAqiFixture: PointAqi = {
  latitude: 28.6139,
  longitude: 77.209,
  estimated_aqi: 355.2,
  category: 'Very Poor',
  method: 'idw_point_interpolation',
  confidence: 0.95,
  as_of: '2025-11-10',
  nearest_city_id: 'delhi',
  nearest_city_name: 'Delhi',
  nearest_city_distance_km: 0.0,
  contributing_cities: [
    { city_id: 'delhi', name: 'Delhi', distance_km: 0.0, weight: 0.01, latest_aqi: 355.2 },
  ],
  nearby_reports_considered: 0,
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('api.ts typed failure handling', () => {
  it('resolves with a typed PointAqi on success', async () => {
    vi.stubGlobal('fetch', vi.fn(async () =>
      new Response(JSON.stringify(pointAqiFixture), { status: 200 }),
    ))
    const res = await getPointAqi(28.6139, 77.209)
    expect('error' in res ? false : res.estimated_aqi).toBe(355.2)
  })

  it('resolves with the ApiError envelope for the outside-India 200 body', async () => {
    vi.stubGlobal('fetch', vi.fn(async () =>
      new Response(JSON.stringify({ error: true, message: 'outside India' }), { status: 200 }),
    ))
    const res = await getPointAqi(40.0, 77.0)
    expect('error' in res && res.error).toBe(true)
    if ('error' in res) expect(res.message).toContain('outside India')
  })

  it('rejects with the envelope message on HTTP failure', async () => {
    vi.stubGlobal('fetch', vi.fn(async () =>
      new Response(JSON.stringify({ error: true, message: 'no monitored city within 400 km' }), { status: 200 }),
    ))
    // getForecast-style 200 envelope resolves; an HTTP failure must reject:
    vi.stubGlobal('fetch', vi.fn(async () =>
      new Response(JSON.stringify({ error: true, message: 'too many reports' }), { status: 429 }),
    ))
    await expect(getPointAqi(0, 0)).rejects.toThrow('too many reports')
  })

  it('rejects with a friendly message on network failure', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => {
      throw new TypeError('Failed to fetch')
    }))
    await expect(getPointAqi(28.6, 77.2)).rejects.toThrow('Cannot reach the backend')
  })
})
