import { Fragment, useEffect, useState } from 'react'
import { CircleMarker, MapContainer, Polyline, TileLayer, Tooltip } from 'react-leaflet'
import { getHotspots } from '../api'
import type { Hotspot } from '../types'
import { INDIA_BOUNDS } from './MapView'
import { SmokeRule } from '../motion'
import TraceWind from './TraceWind'

const SOOT = '#211e1a'
const WIND_INK = '#3b342c'
const PLUME = '#b0763a'

// Cause colours stay inside the warm dust/soot/ember family (no rainbow).
const CAUSE_META: Record<string, { color: string; label: string }> = {
  stubble_burning: { color: '#9e3b18', label: 'Stubble burning' },
  open_burning: { color: '#c08a3e', label: 'Open burning' },
  industrial: { color: '#6e5a46', label: 'Industrial' },
}

// Short wind arrow drawn toward wind_toward (where the wind blows TO).
function arrowEnd(lat: number, lon: number, towardDeg: number, km = 90): [number, number] {
  const rad = (d: number) => (d * Math.PI) / 180
  const dLat = (km * Math.cos(rad(towardDeg))) / 111.0
  const dLon = (km * Math.sin(rad(towardDeg))) / (111.0 * Math.cos(rad(lat)))
  return [lat + dLat, lon + dLon]
}

interface Props {
  onPickCity?: (cityId: string) => void
}

export default function HotspotOverlay({ onPickCity }: Props) {
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

  const fireCount = hotspots.filter((h) => h.cause !== 'industrial').length
  if (error) {
    // keep rendering: the map below still shows city context
  }

  return (
    <div className="panel p-5">
      <div className="mb-1 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-display text-lg font-bold text-soot">Emission hotspots and wind transport</h2>
      </div>
      <p className="measure mt-1 mb-3 text-xs leading-relaxed text-ash">
        {fireCount > 0 ? (
          <>
            Fire detections from the last two days (top 12 by intensity) plus industrial zones. The arrow shows the
            direction the wind blows <em>toward</em>; the dashed line traces the plume to the nearest city inside the
            wind cone, with the travel-time estimate.
          </>
        ) : (
          <>Fire data not loaded — showing industrial zones only. The arrow shows the direction the wind blows <em>toward</em>.</>
        )}
      </p>
      {error && <div className="banner-warn mb-3">{error}</div>}

      <div className="h-[520px] overflow-hidden rounded-sm border border-hairline">
        <MapContainer bounds={INDIA_BOUNDS} boundsOptions={{ padding: [18, 18] }} scrollWheelZoom style={{ height: '100%', width: '100%' }}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {hotspots.map((h) => {
            const meta = CAUSE_META[h.cause] ?? { color: '#7c7367', label: h.cause }
            const hasWind = h.wind_toward_deg != null
            const arrowTo = hasWind ? arrowEnd(h.latitude, h.longitude, h.wind_toward_deg!) : null
            return (
              <Fragment key={h.id}>
                <CircleMarker
                  center={[h.latitude, h.longitude]}
                  radius={7}
                  pathOptions={{ color: SOOT, weight: 1, fillColor: meta.color, fillOpacity: 1 }}
                >
                  <Tooltip className="vayu-tooltip" direction="top">
                    <div className="font-semibold">{meta.label} · {h.id}</div>
                    <div>
                      Confidence <span className="tnum">{(h.confidence * 100).toFixed(0)}%</span>
                      {h.frp != null && (
                        <>
                          {' '}· FRP <span className="tnum">{h.frp.toFixed(0)}</span> MW
                        </>
                      )}
                    </div>
                    {hasWind && (
                      <div>
                        Wind <span className="tnum">{h.wind_speed_ms?.toFixed(1)}</span> m/s from{' '}
                        <span className="tnum">{h.wind_direction_deg?.toFixed(0)}°</span>
                      </div>
                    )}
                    {h.downwind_city_name && (
                      <div>
                        Downwind {h.downwind_city_name} ·{' '}
                        <span className="tnum">{h.distance_km?.toFixed(0)}</span> km · ETA{' '}
                        <span className="tnum">{h.eta_hours?.toFixed(1)}</span> h
                      </div>
                    )}
                  </Tooltip>
                </CircleMarker>
                {arrowTo && (
                  <Polyline positions={[[h.latitude, h.longitude], arrowTo]} pathOptions={{ color: WIND_INK, weight: 2, opacity: 0.85 }} />
                )}
                {h.downwind_city_id && h.downwind_city_name && (
                  <Polyline
                    positions={[
                      [h.latitude, h.longitude],
                      // The downwind marker sits at the city; the API only names
                      // it, so draw to the hotspot-side end using the ETA bearing.
                      arrowEnd(h.latitude, h.longitude, h.wind_toward_deg ?? 0, Math.min(h.distance_km ?? 0, 600)),
                    ]}
                    pathOptions={{ color: PLUME, weight: 2, dashArray: '6 6', opacity: 0.9 }}
                  >
                    <Tooltip className="vayu-tooltip" sticky>
                      Plume toward {h.downwind_city_name} · ETA <span className="tnum">{h.eta_hours?.toFixed(1)}</span> h
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
          <span className="inline-block w-6 border-t-2" style={{ borderColor: WIND_INK }} aria-hidden="true" />
          wind blows toward
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block w-6 border-t-2 border-dashed" style={{ borderColor: PLUME }} aria-hidden="true" />
          plume path (ETA)
        </span>
      </div>

      <SmokeRule className="my-5" />

      <TraceWind hotspots={hotspots} />

      {hotspots.some((h) => h.downwind_city_name) && (
        <div className="flex flex-wrap gap-2 text-xs">
          {hotspots
            .filter((h) => h.downwind_city_name && h.eta_hours != null)
            .slice(0, 8)
            .map((h) => (
              <button
                key={h.id}
                type="button"
                className="btn-quiet"
                onClick={() => onPickCity?.(h.downwind_city_id!)}
                title={`Jump to ${h.downwind_city_name}'s forecast`}
              >
                {meta_label(h)} → {h.downwind_city_name} · ETA {h.eta_hours!.toFixed(1)} h
              </button>
            ))}
        </div>
      )}
    </div>
  )
}

function meta_label(h: Hotspot): string {
  return (CAUSE_META[h.cause] ?? { label: h.cause }).label
}
