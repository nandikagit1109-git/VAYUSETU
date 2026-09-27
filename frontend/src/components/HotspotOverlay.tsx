import { Fragment, useEffect, useState } from 'react'
import L from 'leaflet'
import { CircleMarker, MapContainer, Marker, Polyline, TileLayer, Tooltip } from 'react-leaflet'
import { getHotspots } from '../api'
import type { Hotspot } from '../types'
import { CITY_COORDS, CITY_LABELS } from './MapView'

const ARROW_LENGTH_KM = 90
const SOOT = '#211e1a'
const PANEL = '#f2eee6'
const WIND_INK = '#3b342c' // warm dark ink for the wind vector, so it reads over light tiles
const PLUME = '#b0763a' // ochre dashed plume path

function destPoint(lat: number, lon: number, bearingDeg: number, distKm: number): [number, number] {
  const rad = (d: number) => (d * Math.PI) / 180
  const dLat = (distKm * Math.cos(rad(bearingDeg))) / 111.0
  const dLon = (distKm * Math.sin(rad(bearingDeg))) / (111.0 * Math.cos(rad(lat)))
  return [lat + dLat, lon + dLon]
}

// A drawn arrowhead pointing north, rotated to the wind bearing (compass degrees
// are clockwise from north, matching CSS rotate). Custom SVG, not an icon glyph.
function windArrowSvg(size: number, rotate: number): string {
  return (
    `<svg width="${size}" height="${size}" viewBox="0 0 24 24" aria-hidden="true" ` +
    `style="transform:rotate(${rotate}deg)"><path d="M12 2.5 L20 21 L12 16.5 L4 21 Z" ` +
    `fill="${WIND_INK}" stroke="${PANEL}" stroke-width="1.2" stroke-linejoin="round"/></svg>`
  )
}

function windArrowIcon(bearingDeg: number): L.DivIcon {
  return L.divIcon({
    className: 'wind-arrow-icon',
    html: windArrowSvg(18, bearingDeg),
    iconSize: [18, 18],
    iconAnchor: [9, 9],
  })
}

// Inline React version of the same arrowhead, for the legend (points north).
function WindGlyph() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 2.5 L20 21 L12 16.5 L4 21 Z" fill={WIND_INK} stroke={PANEL} strokeWidth="1.2" strokeLinejoin="round" />
    </svg>
  )
}

// Cause colours stay inside the warm dust/soot/ember family (no violet, no rainbow).
const CAUSE_META: Record<string, { color: string; label: string }> = {
  stubble_burning: { color: '#9e3b18', label: 'Stubble burning' },
  industrial: { color: '#6e5a46', label: 'Industrial' },
  vehicular: { color: '#a89880', label: 'Vehicular' },
  unknown: { color: '#7c7367', label: 'Unknown' },
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
    <div className="panel p-5">
      <h2 className="font-display text-lg font-bold text-soot">Emission hotspots and wind transport</h2>
      <p className="measure mt-1 mb-3 text-xs leading-relaxed text-ash">
        Simulated satellite hotspots with wind vectors. The arrow shows the direction the wind is blowing toward, and
        the dashed line traces the plume to the downwind city.
      </p>
      {error && <div className="banner-warn mb-3">{error}</div>}

      <div className="h-[520px] overflow-hidden rounded-sm border border-hairline">
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
              pathOptions={{ color: SOOT, weight: 2, fillColor: PANEL, fillOpacity: 1 }}
            >
              <Tooltip className="vayu-tooltip" direction="top">
                <span className="font-semibold">{CITY_LABELS[city] ?? city}</span> · city node
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
                  pathOptions={{ color: SOOT, weight: 1, fillColor: meta.color, fillOpacity: 1 }}
                >
                  <Tooltip className="vayu-tooltip" direction="top">
                    <div className="font-semibold">
                      {meta.label} hotspot #{h.id}
                    </div>
                    <div>
                      Confidence <span className="tnum">{(h.confidence * 100).toFixed(0)}%</span>
                    </div>
                    <div>
                      Wind <span className="tnum">{h.wind_speed_kmh}</span> km/h toward{' '}
                      <span className="tnum">{h.wind_direction_deg}°</span>
                    </div>
                    {h.downwind_city && (
                      <div>
                        Downwind {CITY_LABELS[h.downwind_city] ?? h.downwind_city} · ETA{' '}
                        <span className="tnum">{h.eta_hours ?? 'n/a'}</span> h
                      </div>
                    )}
                  </Tooltip>
                </CircleMarker>
                <Polyline positions={[[h.latitude, h.longitude], arrowEnd]} pathOptions={{ color: WIND_INK, weight: 2, opacity: 0.85 }} />
                <Marker position={arrowEnd} icon={windArrowIcon(h.wind_direction_deg)} />
                {downwindPos && (
                  <Polyline
                    positions={[[h.latitude, h.longitude], downwindPos]}
                    pathOptions={{ color: PLUME, weight: 2, dashArray: '6 6', opacity: 0.9 }}
                  >
                    <Tooltip className="vayu-tooltip" sticky>
                      Plume path to {CITY_LABELS[h.downwind_city!] ?? h.downwind_city} · ETA{' '}
                      <span className="tnum">{h.eta_hours ?? 'n/a'}</span> h
                    </Tooltip>
                  </Polyline>
                )}
              </Fragment>
            )
          })}
        </MapContainer>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-ash">
        {Object.values(CAUSE_META).map((m) => (
          <span key={m.label} className="inline-flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: m.color }} aria-hidden="true" />
            {m.label}
          </span>
        ))}
        <span className="inline-flex items-center gap-1.5">
          <WindGlyph />
          wind direction
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block w-6 border-t-2 border-dashed" style={{ borderColor: PLUME }} aria-hidden="true" />
          plume path to downwind city
        </span>
      </div>
    </div>
  )
}
