import { Fragment, useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import { CircleMarker, MapContainer, Marker, Polyline, TileLayer, Tooltip } from 'react-leaflet'
import { animate, useReducedMotion } from 'framer-motion'
import { getHotspots } from '../api'
import type { Hotspot } from '../types'
import { CITIES, CITY_COORDS, cityLabel, INDIA_BOUNDS, isCohort } from '../cities'
import { EASE, SmokeRule } from '../motion'
import TraceWind from './TraceWind'

const ARROW_LENGTH_KM = 90
const SOOT = '#211e1a'
const PANEL = '#f2eee6'
const WIND_INK = '#3b342c' // warm dark ink for the wind vector, so it reads over light tiles
const OCHRE = '#b0763a' // federation ochre: cohort city nodes and plume paths
const PLUME = OCHRE

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

const VECTOR_DRAW_S = 0.9

// A wind vector that draws itself in (SmokePath behaviour, applied to the Leaflet
// SVG path). The arrowhead marker only appears once the stroke has landed.
function WindVector({ from, to, bearing, delay }: { from: [number, number]; to: [number, number]; bearing: number; delay: number }) {
  const reduced = useReducedMotion()
  const lineRef = useRef<L.Polyline | null>(null)
  const [drawn, setDrawn] = useState(Boolean(reduced))
  const geometryKey = `${from[0]},${from[1]}-${to[0]},${to[1]}`

  useEffect(() => {
    if (reduced) {
      setDrawn(true)
      return
    }
    setDrawn(false)
    let frame = 0
    let ctrl: { stop: () => void } | null = null
    const finish = () => {
      const el = lineRef.current?.getElement() as SVGPathElement | null | undefined
      if (el) {
        el.style.strokeDasharray = ''
        el.style.strokeDashoffset = ''
      }
      setDrawn(true)
    }
    const start = () => {
      const el = lineRef.current?.getElement() as SVGPathElement | null | undefined
      const len = el?.getTotalLength?.() ?? 0
      if (!el || !len) {
        // The renderer has not attached the path yet; try once more next frame.
        frame = requestAnimationFrame(start)
        return
      }
      el.style.strokeDasharray = String(len)
      el.style.strokeDashoffset = String(len)
      ctrl = animate(len, 0, {
        duration: VECTOR_DRAW_S,
        ease: EASE,
        delay,
        onUpdate: (v) => {
          el.style.strokeDashoffset = String(v)
        },
        onComplete: finish,
      })
    }
    frame = requestAnimationFrame(start)
    // Backstop: a throttled frame loop must not leave the vector hidden mid-draw.
    const backstop = window.setTimeout(() => {
      ctrl?.stop()
      finish()
    }, (delay + VECTOR_DRAW_S) * 1000 + 250)
    return () => {
      cancelAnimationFrame(frame)
      window.clearTimeout(backstop)
      ctrl?.stop()
    }
  }, [reduced, delay, geometryKey])

  return (
    <>
      <Polyline ref={lineRef} positions={[from, to]} pathOptions={{ color: WIND_INK, weight: 2, opacity: 0.85 }} />
      {drawn && <Marker position={to} icon={windArrowIcon(bearing)} />}
    </>
  )
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
        <MapContainer bounds={INDIA_BOUNDS} boundsOptions={{ padding: [24, 24] }} scrollWheelZoom style={{ height: '100%', width: '100%' }}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {CITIES.map((c) => {
            const cohort = isCohort(c.key)
            return (
              <CircleMarker
                key={c.key}
                center={[c.lat, c.lon]}
                radius={cohort ? 8 : 5}
                pathOptions={{
                  color: SOOT,
                  weight: cohort ? 2 : 1.4,
                  fillColor: cohort ? OCHRE : PANEL,
                  fillOpacity: 1,
                }}
              >
                <Tooltip className="vayu-tooltip" direction="top">
                  <span className="font-semibold">{c.label}</span> ·{' '}
                  {cohort ? 'federated cohort node' : 'city node'}
                </Tooltip>
              </CircleMarker>
            )
          })}
          {hotspots.map((h, i) => {
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
                        Downwind {cityLabel(h.downwind_city)} · ETA{' '}
                        <span className="tnum">{h.eta_hours ?? 'n/a'}</span> h
                      </div>
                    )}
                  </Tooltip>
                </CircleMarker>
                <WindVector
                  from={[h.latitude, h.longitude]}
                  to={arrowEnd}
                  bearing={h.wind_direction_deg}
                  // Stagger caps out: an all-India hotspot list would otherwise
                  // leave the last vectors waiting several seconds to draw.
                  delay={0.2 + Math.min(i, 7) * 0.25}
                />
                {downwindPos && (
                  <Polyline
                    positions={[[h.latitude, h.longitude], downwindPos]}
                    pathOptions={{ color: PLUME, weight: 2, dashArray: '6 6', opacity: 0.9 }}
                  >
                    <Tooltip className="vayu-tooltip" sticky>
                      Plume path to {cityLabel(h.downwind_city!)} · ETA{' '}
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

      <SmokeRule className="my-5" />

      <TraceWind hotspots={hotspots} />
    </div>
  )
}
