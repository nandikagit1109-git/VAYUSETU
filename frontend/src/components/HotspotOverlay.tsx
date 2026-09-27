import { Fragment, useEffect, useState } from 'react'
import L from 'leaflet'
import { CircleMarker, MapContainer, Marker, Polyline, TileLayer, Tooltip } from 'react-leaflet'
import { getHotspots } from '../api'
import type { Hotspot } from '../types'
import { CITY_COORDS, CITY_LABELS } from './MapView'

const ARROW_LENGTH_KM = 90

function destPoint(lat: number, lon: number, bearingDeg: number, distKm: number): [number, number] {
  const rad = (d: number) => (d * Math.PI) / 180
  const dLat = (distKm * Math.cos(rad(bearingDeg))) / 111.0
  const dLon = (distKm * Math.sin(rad(bearingDeg))) / (111.0 * Math.cos(rad(lat)))
  return [lat + dLat, lon + dLon]
}

function arrowIcon(bearingDeg: number, color: string): L.DivIcon {
  // The ➤ glyph points east (90° compass), so rotate by bearing-90.
  return L.divIcon({
    className: 'wind-arrow-icon',
    html: `<div style="transform:rotate(${bearingDeg - 90}deg);color:${color};font-size:18px;line-height:20px;text-align:center;">➤</div>`,
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  })
}

const CAUSE_META: Record<string, { color: string; label: string }> = {
  stubble_burning: { color: '#fb923c', label: 'Stubble burning' },
  industrial: { color: '#ef4444', label: 'Industrial' },
  vehicular: { color: '#a78bfa', label: 'Vehicular' },
  unknown: { color: '#94a3b8', label: 'Unknown' },
}

export default function HotspotOverlay() {
  const [hotspots, setHotspots] = useState<Hotspot[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    getHotspots()
      .then((d) => {
        if (active) setHotspots(d.hotspots ?? [])
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : 'Could not load hotspots.')
      })
    return () => {
      active = false
    }
  }, [])

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <h2 className="mb-1 text-lg font-semibold">Emission Hotspots & Wind Transport</h2>
      <p className="mb-3 text-xs text-slate-400">
        Simulated satellite hotspots with wind vectors (arrow = wind direction) and dashed plume paths to the downwind city.
      </p>
      {error && <div className="mb-3 rounded-lg border border-red-800 bg-red-950/60 px-3 py-2 text-xs text-red-300">{error}</div>}
      <div className="h-[480px] overflow-hidden rounded-lg">
        <MapContainer center={[28.6, 77.6]} zoom={6} scrollWheelZoom style={{ height: '100%', width: '100%' }}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {Object.entries(CITY_COORDS).map(([city, pos]) => (
            <CircleMarker
              key={city}
              center={pos}
              radius={8}
              pathOptions={{ color: '#e2e8f0', fillColor: '#0ea5e9', fillOpacity: 0.9, weight: 2 }}
            >
              <Tooltip className="vayu-tooltip" direction="top">
                {CITY_LABELS[city] ?? city}
              </Tooltip>
            </CircleMarker>
          ))}
          {hotspots.map((h) => {
            const meta = CAUSE_META[h.cause] ?? CAUSE_META.unknown
            const arrowEnd = destPoint(h.latitude, h.longitude, h.wind_direction_deg, ARROW_LENGTH_KM)
            const downwindPos = h.downwind_city ? CITY_COORDS[h.downwind_city] : null
            return (
              <Fragment key={h.id}>
                <CircleMarker
                  center={[h.latitude, h.longitude]}
                  radius={7}
                  pathOptions={{ color: '#0f172a', fillColor: meta.color, fillOpacity: 0.95, weight: 1 }}
                >
                  <Tooltip className="vayu-tooltip" direction="top">
                    <div>
                      <div className="font-semibold">{meta.label} hotspot #{h.id}</div>
                      <div>Confidence: {(h.confidence * 100).toFixed(0)}%</div>
                      <div>Wind: {h.wind_speed_kmh} km/h toward {h.wind_direction_deg}°</div>
                      {h.downwind_city && (
                        <div>
                          Downwind: {CITY_LABELS[h.downwind_city] ?? h.downwind_city} · ETA {h.eta_hours ?? '—'} h
                        </div>
                      )}
                    </div>
                  </Tooltip>
                </CircleMarker>
                <Polyline positions={[[h.latitude, h.longitude], arrowEnd]} pathOptions={{ color: '#38bdf8', weight: 2.5 }} />
                <Marker position={arrowEnd} icon={arrowIcon(h.wind_direction_deg, '#38bdf8')} />
                {downwindPos && (
                  <Polyline
                    positions={[[h.latitude, h.longitude], downwindPos]}
                    pathOptions={{ color: '#fbbf24', weight: 2, dashArray: '6 6', opacity: 0.85 }}
                  >
                    <Tooltip className="vayu-tooltip" sticky>
                      Plume path → {CITY_LABELS[h.downwind_city!] ?? h.downwind_city} · ETA {h.eta_hours ?? '—'} h
                    </Tooltip>
                  </Polyline>
                )}
              </Fragment>
            )
          })}
        </MapContainer>
      </div>
      <div className="mt-3 flex flex-wrap gap-3 text-xs text-slate-400">
        {Object.values(CAUSE_META).map((m) => (
          <span key={m.label} className="inline-flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: m.color }} />
            {m.label}
          </span>
        ))}
        <span className="inline-flex items-center gap-1.5">
          <span style={{ color: '#38bdf8' }}>➤</span> wind direction
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block w-6 border-t-2 border-dashed border-amber-400" /> plume path to downwind city
        </span>
      </div>
    </div>
  )
}
