import { useEffect, useMemo, useRef, useState } from 'react'
import { animate, motion, useReducedMotion } from 'framer-motion'
import type { Hotspot } from '../types'
import { EASE, FadeUp } from '../motion'

const SOOT = '#211e1a'
const PANEL = '#f2eee6'
const OCHRE = '#b0763a'
const EMBER = '#9e3b18'
const ASH = '#7c7367'

const X0 = 20
const X1 = 380
const SPAN = X1 - X0
const SNAP_POINTS = [0, 0.5, 1]

const clamp01 = (v: number) => Math.min(1, Math.max(0, v))
const nearestSnap = (t: number) => SNAP_POINTS.reduce((a, b) => (Math.abs(b - t) < Math.abs(a - t) ? b : a), SNAP_POINTS[0])

interface TraceWindProps {
  hotspots: Hotspot[]
}

// "Trace the Wind": drag the handle along a hotspot -> downwind city path to
// read how far the plume has travelled and how much strength it keeps.
export default function TraceWind({ hotspots }: TraceWindProps) {
  const reduced = useReducedMotion()
  const candidates = useMemo(() => hotspots.filter((h) => h.downwind_city_id != null && h.eta_hours != null), [hotspots])
  const [sel, setSel] = useState(0)
  const [t, setT] = useState(0)
  const [dragging, setDragging] = useState(false)
  const [snapCount, setSnapCount] = useState(0)
  const svgRef = useRef<SVGSVGElement | null>(null)
  const tRef = useRef(0)
  // Drag state lives in a ref as well as state: the guard must hold for a move
  // that arrives before React has re-rendered the pointerdown.
  const dragRef = useRef(false)

  const h = candidates[sel]

  useEffect(() => {
    if (sel > candidates.length - 1) setSel(0)
  }, [candidates.length, sel])

  // Reset the handle when the chosen hotspot changes.
  useEffect(() => {
    tRef.current = 0
    setT(0)
    setSnapCount((c) => c + 1)
  }, [sel, h?.id])

  function tFromClientX(clientX: number): number {
    const el = svgRef.current
    if (!el) return 0
    const rect = el.getBoundingClientRect()
    if (rect.width === 0) return 0
    const vx = ((clientX - rect.left) / rect.width) * 400
    return clamp01((vx - X0) / SPAN)
  }

  function onPointerDown(e: React.PointerEvent<SVGSVGElement>) {
    if (!h) return
    e.currentTarget.setPointerCapture(e.pointerId)
    dragRef.current = true
    setDragging(true)
    const next = tFromClientX(e.clientX)
    tRef.current = next
    setT(next)
  }

  function onPointerMove(e: React.PointerEvent<SVGSVGElement>) {
    if (!dragRef.current || !h) return
    const next = tFromClientX(e.clientX)
    tRef.current = next
    setT(next)
  }

  function onPointerUp() {
    if (!dragRef.current || !h) return
    dragRef.current = false
    setDragging(false)
    const target = nearestSnap(tRef.current)
    if (reduced) {
      tRef.current = target
      setT(target)
    } else {
      animate(tRef.current, target, {
        type: 'spring',
        stiffness: 300,
        damping: 20,
        onUpdate: (v) => {
          tRef.current = v
          setT(v)
        },
      })
    }
    setSnapCount((c) => c + 1)
  }

  function step(dir: -1 | 1) {
    const i = SNAP_POINTS.indexOf(nearestSnap(tRef.current))
    const target = SNAP_POINTS[Math.min(SNAP_POINTS.length - 1, Math.max(0, i + dir))]
    if (reduced) {
      tRef.current = target
      setT(target)
    } else {
      animate(tRef.current, target, {
        duration: 0.4,
        ease: EASE,
        onUpdate: (v) => {
          tRef.current = v
          setT(v)
        },
      })
    }
    setSnapCount((c) => c + 1)
  }

  if (candidates.length === 0) {
    return (
      <div className="rounded-sm border border-hairline bg-panel/60 p-4 text-xs text-ash">
        No hotspot in the current set has a city downwind of it, so there is no plume path to trace yet.
      </div>
    )
  }

  const city = h.downwind_city_name ?? h.downwind_city_id!
  const eta = h.eta_hours ?? 0
  const elapsed = eta * t
  const remaining = eta * (1 - t)
  // Demo-scale estimate: a confidence-weighted peak contribution that loses up
  // to 45% of its strength to dilution between the hotspot and the city.
  const aqiImpact = Math.round(h.confidence * 180 * (1 - 0.45 * t))
  const handleX = X0 + t * SPAN
  const atCity = t > 0.985

  return (
    <div className="rounded-sm border border-hairline bg-panel/60 p-4">
      <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h3 className="font-display text-sm font-bold text-soot">Trace the wind</h3>
          <p className="mt-0.5 text-xs text-ash">
            Drag the handle from the hotspot toward {city} to see how the plume ages on the way.
          </p>
        </div>
        <label className="flex items-center gap-2 text-xs text-ash">
          <span className="label">Hotspot</span>
          <select
            className="field py-1"
            value={sel}
            onChange={(e) => setSel(Number(e.target.value))}
            aria-label="Choose a hotspot to trace"
          >
            {candidates.map((c, i) => (
              <option key={c.id} value={i}>
                {c.cause.replace('_', ' ')} → {c.downwind_city_name} · ETA {c.eta_hours?.toFixed(1)} h
              </option>
            ))}
          </select>
        </label>
      </div>

      <svg
        ref={svgRef}
        viewBox="0 0 400 92"
        className="w-full touch-none select-none"
        style={{ height: 'auto' }}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        role="slider"
        tabIndex={0}
        aria-label={`Plume position between hotspot ${h.id} and ${city}`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(t * 100)}
        aria-valuetext={`${Math.round(t * 100)}% of the way to ${city}`}
        onKeyDown={(e) => {
          if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') {
            e.preventDefault()
            step(-1)
          } else if (e.key === 'ArrowRight' || e.key === 'ArrowUp') {
            e.preventDefault()
            step(1)
          }
        }}
      >
        {/* base vector */}
        <line x1={X0} y1={46} x2={X1} y2={46} stroke="rgba(33,30,26,0.18)" strokeWidth={1} strokeDasharray="4 5" />

        {/* travelled plume, live while dragging */}
        <line x1={X0} y1={46} x2={handleX} y2={46} stroke={OCHRE} strokeWidth={3} strokeLinecap="round" opacity={0.9} />

        {/* midpoint tick */}
        <line x1={X0 + SPAN / 2} y1={38} x2={X0 + SPAN / 2} y2={54} stroke="rgba(33,30,26,0.25)" strokeWidth={1} />

        {/* endpoints */}
        <circle cx={X0} cy={46} r={6} fill={EMBER} stroke={SOOT} strokeWidth={1} />
        <circle cx={X1} cy={46} r={6} fill={PANEL} stroke={SOOT} strokeWidth={2} />
        <text x={X0} y={26} textAnchor="middle" fontSize="10" fill={ASH} fontFamily="IBM Plex Mono, monospace">
          hotspot
        </text>
        <text x={X1} y={26} textAnchor="middle" fontSize="10" fill={ASH} fontFamily="IBM Plex Mono, monospace">
          {city}
        </text>

        {/* draggable handle */}
        <motion.g animate={{ x: handleX }} transition={{ duration: 0 }}>
          <motion.g
            animate={{ scale: dragging ? 1.15 : 1 }}
            transition={{ type: 'spring', stiffness: 300, damping: 20 }}
            style={{ transformBox: 'fill-box', transformOrigin: 'center' }}
          >
            <g transform="translate(0,46)">
              <circle r={11} fill={PANEL} stroke={SOOT} strokeWidth={2} />
              <path
                d="M-4 0 L4 0 M1.5 -3 L4.5 0 L1.5 3"
                stroke={SOOT}
                strokeWidth={1.6}
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </g>
          </motion.g>
        </motion.g>

        <text x={200} y={84} textAnchor="middle" fontSize="10" fill={ASH} fontFamily="IBM Plex Sans, sans-serif">
          {atCity ? 'plume has reached the city' : 'drag the handle, or use the arrow keys'}
        </text>
      </svg>

      <FadeUp key={`${h.id}-${snapCount}`} className="mt-3">
        <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-soot">
          <span>
            <span className="label mr-1.5">Covered</span>
            <span className="tnum">{Math.round(t * 100)}%</span> of the path
          </span>
          <span>
            <span className="label mr-1.5">Elapsed</span>
            <span className="tnum">{elapsed.toFixed(1)}</span> h · <span className="tnum">{remaining.toFixed(1)}</span> h to arrival
          </span>
          <span>
            <span className="label mr-1.5">Est. AQI added</span>
            <span className="tnum">{aqiImpact}</span>
            <span className="text-ash"> after {Math.round(45 * t)}% dilution</span>
          </span>
        </div>
      </FadeUp>
    </div>
  )
}
