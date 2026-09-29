import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { submitReport } from '../api'
import type { CitizenReport, ReportResult } from '../types'
import { aqiColor } from './AqiBadge'

type Visibility = '' | 'clear' | 'hazy' | 'very_hazy'

interface Props {
  pinnedLatLon: { lat: number; lon: number }
  onCreated: (report: CitizenReport, result: ReportResult) => void
}

// ReportForm: the server assigns the city from the pinned coordinates (there is
// no client city field in the v2 contract, trap 15). Latitude/longitude come
// from a map click or the "use city centre" control on the selected city.
// The lat/lon fields track the pin while the user has not typed over them —
// otherwise a map click updates the pin but the form silently submits the
// old coordinates (this exact stale-pin bug broke a recorded demo run).
export default function ReportForm({ pinnedLatLon, onCreated }: Props) {
  const [lat, setLat] = useState(String(pinnedLatLon.lat.toFixed(4)))
  const [lon, setLon] = useState(String(pinnedLatLon.lon.toFixed(4)))
  const [coordsDirty, setCoordsDirty] = useState(false)

  useEffect(() => {
    if (coordsDirty) return
    setLat(pinnedLatLon.lat.toFixed(4))
    setLon(pinnedLatLon.lon.toFixed(4))
  }, [pinnedLatLon.lat, pinnedLatLon.lon, coordsDirty])
  const [visibility, setVisibility] = useState<Visibility>('')
  const [photoBase64, setPhotoBase64] = useState<string | null>(null)
  const [photoName, setPhotoName] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<ReportResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  function handlePhoto(file: File | null) {
    setResult(null)
    setError(null)
    if (!file) {
      setPhotoBase64(null)
      setPhotoName(null)
      return
    }
    const reader = new FileReader()
    reader.onload = () => {
      setPhotoBase64(typeof reader.result === 'string' ? reader.result : null)
      setPhotoName(file.name)
    }
    reader.onerror = () => setError('Could not read the selected photo. Try the visibility dropdown instead.')
    reader.readAsDataURL(file)
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setResult(null)

    const latitude = Number(lat)
    const longitude = Number(lon)
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
      setError('Latitude and longitude must be valid numbers.')
      return
    }
    if (latitude < 6.5 || latitude > 37.5 || longitude < 68.0 || longitude > 97.5) {
      setError('Coordinates must be inside India (lat 6.5-37.5, lon 68.0-97.5).')
      return
    }
    if (!photoBase64 && !visibility) {
      setError('Attach a photo or choose a manual visibility level.')
      return
    }

    setSubmitting(true)
    try {
      const res = await submitReport({
        latitude,
        longitude,
        photo_base64: photoBase64,
        manual_visibility: (visibility || null) as 'clear' | 'hazy' | 'very_hazy' | null,
      })
      setResult(res)
      onCreated(
        {
          id: res.id,
          latitude,
          longitude,
          city_id: res.city_id,
          haze_score: res.haze_score,
          confidence: res.confidence,
          trust_weight: res.trust_weight,
          source: 'user',
          created_at: new Date().toISOString(),
        },
        res,
      )
      setPhotoBase64(null)
      setPhotoName(null)
      setVisibility('')
      const photoInput = document.getElementById('report-photo-input') as HTMLInputElement | null
      if (photoInput) photoInput.value = ''
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Submit failed. Is the backend running?')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="panel p-5" data-tour="report-form">
      <h2 className="font-display text-lg font-bold text-soot">Citizen Report</h2>
      <p className="measure mt-1 mb-4 text-xs leading-relaxed text-ash">
        Click the map to drop the report location (or use the selected city&apos;s centre). The server assigns
        the nearest city within coverage. Scored as a <strong>heuristic estimate</strong>, not a measurement.
      </p>

      <div className="mb-3 grid grid-cols-2 gap-3">
        <div>
          <label className="label" htmlFor="report-lat">
            Latitude
          </label>
          <input
            id="report-lat"
            className="field tnum"
            type="number"
            step="any"
            value={lat}
            onChange={(e) => {
              setCoordsDirty(true)
              setLat(e.target.value)
            }}
          />
        </div>
        <div>
          <label className="label" htmlFor="report-lon">
            Longitude
          </label>
          <input
            id="report-lon"
            className="field tnum"
            type="number"
            step="any"
            value={lon}
            onChange={(e) => {
              setCoordsDirty(true)
              setLon(e.target.value)
            }}
          />
        </div>
      </div>

      <label className="label" htmlFor="report-photo-input">
        Sky photo (optional)
      </label>
      <input
        id="report-photo-input"
        type="file"
        accept="image/*"
        onChange={(e) => handlePhoto(e.target.files?.[0] ?? null)}
        className="mb-3 w-full text-xs text-ash file:mr-3 file:cursor-pointer file:rounded-sm file:border file:border-hairline-strong file:bg-panel file:px-3 file:py-2 file:text-xs file:font-medium file:text-soot hover:file:bg-haze"
      />
      {photoName && <p className="mb-3 -mt-1 text-xs text-ash">Selected: {photoName}</p>}

      <label className="label" htmlFor="report-visibility">
        Manual visibility (optional)
      </label>
      <select
        id="report-visibility"
        value={visibility}
        onChange={(e) => setVisibility(e.target.value as Visibility)}
        className="field mb-4"
      >
        <option value="">Not provided</option>
        <option value="clear">Clear</option>
        <option value="hazy">Hazy</option>
        <option value="very_hazy">Very hazy</option>
      </select>

      <button type="submit" disabled={submitting} className="btn-primary w-full">
        {submitting ? 'Scoring…' : 'Submit report'}
      </button>

      {error && <div className="banner-warn mt-3">{error}</div>}
      {result && (
        <div className="note mt-3">
          <span className="font-semibold text-soot">Report #{result.id} assigned to {result.city_id}:</span>{' '}
          <span className="tnum font-semibold" style={{ color: aqiColor(result.haze_score) }}>
            {result.haze_score.toFixed(0)} / 500
          </span>{' '}
          <span className="text-ash">
            · heuristic estimate · trust <span className="tnum">{result.trust_weight.toFixed(2)}</span> · pin added
          </span>
        </div>
      )}
    </form>
  )
}
