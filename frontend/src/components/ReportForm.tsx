import { useState } from 'react'
import type { FormEvent } from 'react'
import { submitReport } from '../api'
import type { CitizenReport } from '../types'
import { CITY_COORDS, CITY_LABELS, hazeColor } from './MapView'

interface Props {
  onCreated: (report: CitizenReport) => void
}

type Visibility = '' | 'clear' | 'hazy' | 'very_hazy'

export default function ReportForm({ onCreated }: Props) {
  const [city, setCity] = useState('delhi')
  const [lat, setLat] = useState(String(CITY_COORDS.delhi[0]))
  const [lon, setLon] = useState(String(CITY_COORDS.delhi[1]))
  const [visibility, setVisibility] = useState<Visibility>('')
  const [photoBase64, setPhotoBase64] = useState<string | null>(null)
  const [photoName, setPhotoName] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<CitizenReport | null>(null)
  const [error, setError] = useState<string | null>(null)

  function handleCityChange(next: string) {
    setCity(next)
    const coords = CITY_COORDS[next]
    if (coords) {
      setLat(String(coords[0]))
      setLon(String(coords[1]))
    }
  }

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
    if (
      !Number.isFinite(latitude) ||
      !Number.isFinite(longitude) ||
      latitude < -90 ||
      latitude > 90 ||
      longitude < -180 ||
      longitude > 180
    ) {
      setError('Latitude and longitude must be valid numbers.')
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
        city,
        photo_base64: photoBase64,
        manual_visibility: (visibility || null) as 'clear' | 'hazy' | 'very_hazy' | null,
      })
      const pin: CitizenReport = {
        id: res.id,
        latitude,
        longitude,
        city,
        haze_score: res.haze_score,
        confidence: res.confidence,
        trust_weight: 1.0,
        created_at: new Date().toISOString(),
      }
      setResult(pin)
      onCreated(pin)
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
    <form onSubmit={handleSubmit} className="panel p-5">
      <h2 className="font-display text-lg font-bold text-soot">Citizen Report</h2>
      <p className="measure mt-1 mb-4 text-xs leading-relaxed text-ash">
        Submit a sky photo or a manual visibility reading. You get an instant haze/AQI-proxy score and a pin on the map.
      </p>

      <label className="label" htmlFor="report-city">
        City
      </label>
      <select
        id="report-city"
        value={city}
        onChange={(e) => handleCityChange(e.target.value)}
        className="field mb-3"
      >
        {Object.keys(CITY_COORDS).map((c) => (
          <option key={c} value={c}>
            {CITY_LABELS[c] ?? c}
          </option>
        ))}
      </select>

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
            onChange={(e) => setLat(e.target.value)}
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
            onChange={(e) => setLon(e.target.value)}
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
          <span className="font-semibold text-soot">Report #{result.id} scored:</span>{' '}
          <span className="tnum font-semibold" style={{ color: hazeColor(result.haze_score) }}>
            haze {result.haze_score.toFixed(0)} / 500
          </span>{' '}
          <span className="text-ash">
            · confidence <span className="tnum">{(result.confidence * 100).toFixed(0)}%</span> · pin added to map
          </span>
        </div>
      )}
    </form>
  )
}
