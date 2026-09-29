import { useState } from 'react'
import { getPointAqi } from '../api'
import type { PointAqi } from '../types'

interface Props {
  /** Lat/lon picked on the map; the card queries this point. */
  pin: { lat: number; lon: number }
}

function confidenceLabel(c: number): { text: string; tone: string } {
  if (c > 0.7) return { text: 'high confidence', tone: 'text-soot' }
  if (c > 0.4) return { text: 'moderate confidence', tone: 'text-soot' }
  return { text: 'rough estimate', tone: 'text-ash' }
}

// "Check any location" (spec section 13, tab 1): air quality for ANY point in
// India, not just registry cities. Shows the estimate, its category and an
// honest confidence note; never presents a low-confidence number as precise.
export default function PointAqiCard({ pin }: Props) {
  const [result, setResult] = useState<PointAqi | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [queried, setQueried] = useState<{ lat: number; lon: number } | null>(null)

  async function check(lat: number, lon: number) {
    setLoading(true)
    setError(null)
    try {
      const res = await getPointAqi(lat, lon)
      if ('error' in res) {
        setError(res.message)
        setResult(null)
      } else {
        setResult(res)
        setQueried({ lat, lon })
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not reach the server.')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  async function useGeolocation() {
    if (!('geolocation' in navigator)) {
      setError('Geolocation is not available in this browser.')
      return
    }
    setLoading(true)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLoading(false)
        void check(pos.coords.latitude, pos.coords.longitude)
      },
      () => {
        setLoading(false)
        setError('Location permission was declined.')
      },
      { timeout: 8000 },
    )
  }

  const conf = result ? confidenceLabel(result.confidence) : null
  const far = result && result.nearest_city_distance_km > 300

  return (
    <div className="panel p-5">
      <h3 className="text-sm font-semibold text-soot">Check any location</h3>
      <p className="mt-1 text-xs leading-relaxed text-ash">
        Air quality for any point in India — pick a spot on the map, then check it here. Not just the {28} registry cities.
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          className="btn-quiet flex-1"
          disabled={loading}
          onClick={() => void check(pin.lat, pin.lon)}
        >
          {loading ? 'Checking…' : `Check pin (${pin.lat.toFixed(3)}, ${pin.lon.toFixed(3)})`}
        </button>
        <button type="button" className="btn-quiet" disabled={loading} onClick={() => void useGeolocation()}>
          Use my location
        </button>
      </div>

      {error && <div className="banner-warn mt-3">{error}</div>}

      {result && (
        <div className="mt-3 text-xs leading-relaxed text-ash">
          <div className="flex items-baseline gap-2">
            <span className="font-display text-2xl font-extrabold text-soot">{result.estimated_aqi}</span>
            <span className="font-medium text-soot">{result.category}</span>
            <span className="ml-auto">{conf?.text}</span>
          </div>
          <p className="mt-1">
            Nearest monitored city: {result.nearest_city_name} ({result.nearest_city_distance_km} km)
            {far ? ' — rough estimate, no monitor nearby' : ''}. Ground data as of {result.as_of}.
          </p>
          {result.nearby_reports_considered > 0 && (
            <p>{result.nearby_reports_considered} citizen report(s) within 50 km folded in.</p>
          )}
          {queried && (
            <p className="mt-1 text-[11px]">
              Queried at {queried.lat.toFixed(4)}, {queried.lon.toFixed(4)} · method {result.method}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
