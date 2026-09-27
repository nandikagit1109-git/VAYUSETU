import { useEffect, useRef, useState } from 'react'
import type { CSSProperties } from 'react'
import { AnimatePresence, animate, motion, useMotionTemplate, useMotionValue, useReducedMotion } from 'framer-motion'
import { DUR, EASE } from '../motion'

const OCHRE = '#b0763a'
const MOVE_MS = 600
// Placement estimate for the caption box; it is clamped to the viewport edges.
const CAPTION_W = 340
const CAPTION_H = 200

export interface TourStep {
  target: string
  tab?: string
  title: string
  body: string
}

export const TOUR_STEPS: TourStep[] = [
  {
    target: 'tabs',
    title: 'Four sections, one network',
    body: 'Map and report, federated training, hotspots with forecast, and alerts. Everything runs against local mock data by default, so it works offline.',
  },
  {
    target: 'report-form',
    tab: 'map',
    title: 'File an observation',
    body: 'Type a city and the plume line follows your typing. Submit with a photo or a visibility guess and the API returns a haze score plus a confidence value.',
  },
  {
    target: 'map',
    tab: 'map',
    title: 'Pins land on the map',
    body: 'Each report is plotted where it was filed and coloured by severity. The three federated cohort nodes are marked in ochre; every other city stays a quiet outline so citizen readings are the loud marks.',
  },
  {
    target: 'fed-chart',
    tab: 'federated',
    title: 'Weights travel, data does not',
    body: 'Start a run and watch three faint local loss lines draw in, then the aggregated global line. No raw observation is ever pooled on the server.',
  },
  {
    target: 'alerts-list',
    tab: 'alerts',
    title: 'Thresholds become actions',
    body: 'When a 72-hour forecast crosses a GRAP threshold, the alert carries the real graded-response action for that stage, and can be acknowledged here.',
  },
]

interface SpotlightTourProps {
  onNavigate: (tab: string) => void
  onClose: () => void
}

interface Hole {
  x: number
  y: number
  rx: number
  ry: number
}

// "Show me around": a scrim with a radial mask hole that travels between targets.
// The caption only fades in once the spotlight has finished moving, so the reader
// is never looking at text while the frame is still travelling.
export default function SpotlightTour({ onNavigate, onClose }: SpotlightTourProps) {
  const reduced = useReducedMotion()
  const [step, setStep] = useState(0)
  const [hole, setHole] = useState<Hole | null>(null)
  const [captionReady, setCaptionReady] = useState(false)
  const mx = useMotionValue(typeof window === 'undefined' ? 400 : window.innerWidth / 2)
  const my = useMotionValue(typeof window === 'undefined' ? 300 : window.innerHeight / 2)
  const mrx = useMotionValue(0)
  const mry = useMotionValue(0)
  const stepTimers = useRef<number[]>([])
  const moveTimers = useRef<number[]>([])
  const remeasure = useRef<() => void>(() => {})

  // The hole is an ellipse so a wide, short target (the tab bar) is not lit by a
  // circle the size of the page. It shrinks when the caption would otherwise have
  // nowhere to sit that does not cover the target.
  const holeFor = (r: DOMRect): Hole => {
    const vw = window.innerWidth
    const vh = window.innerHeight
    const x = r.left + r.width / 2
    const y = r.top + r.height / 2
    const room = Math.max(vh - CAPTION_H - 32 - y, y - CAPTION_H - 24)
    return {
      x,
      y,
      rx: Math.min(r.width / 2 + 28, vw * 0.46),
      ry: Math.min(r.height / 2 + 28, vh * 0.42, Math.max(52, room)),
    }
  }

  const readTarget = (target: string, scroll: boolean): boolean => {
    const el = document.querySelector(`[data-tour="${target}"]`)
    if (!el) return false
    // Instant jump, not smooth: measuring while the page is still scrolling would
    // park the spotlight on empty space. The spotlight move is the tour's motion.
    if (scroll) el.scrollIntoView({ block: 'center', behavior: 'auto' })
    const r = el.getBoundingClientRect()
    if (r.width === 0 && r.height === 0) return false
    setHole(holeFor(r))
    return true
  }

  useEffect(() => {
    const s = TOUR_STEPS[step]
    if (!s) return
    setCaptionReady(false)
    remeasure.current = () => readTarget(s.target, false)

    // The target may still be mounting (a tab crossfade is in flight), so retry a
    // few times before falling back to a centred hole. The caption must always be
    // readable, even if the element it describes cannot be found.
    const attempt = (n: number) => {
      if (readTarget(s.target, true)) return
      if (n < 4) {
        stepTimers.current.push(window.setTimeout(() => attempt(n + 1), 220))
        return
      }
      setHole({
        x: window.innerWidth / 2,
        y: window.innerHeight / 2,
        rx: Math.min(window.innerWidth * 0.4, 260),
        ry: Math.min(window.innerHeight * 0.28, 140),
      })
    }

    if (s.tab) {
      onNavigate(s.tab)
      // Wait out the tab crossfade before measuring, or the target is not mounted yet.
      stepTimers.current.push(window.setTimeout(() => attempt(0), reduced ? 80 : DUR * 1000 + 140))
    } else {
      // Scroll first, then measure once the scroll has landed.
      const el = document.querySelector(`[data-tour="${s.target}"]`)
      el?.scrollIntoView({ block: 'center', behavior: 'auto' })
      stepTimers.current.push(window.setTimeout(() => attempt(0), 200))
    }

    return () => {
      stepTimers.current.forEach((t) => window.clearTimeout(t))
      stepTimers.current = []
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, reduced])

  useEffect(() => {
    if (!hole) return
    const opts = reduced ? { duration: 0 } : { duration: MOVE_MS / 1000, ease: EASE }
    const ctrls = [
      animate(mx, hole.x, opts),
      animate(my, hole.y, opts),
      animate(mrx, hole.rx, opts),
      animate(mry, hole.ry, opts),
    ]
    // Backstop: if the frame loop is throttled (backgrounded tab) the tween never
    // lands, so snap the hole to its end state instead of leaving a closed scrim.
    moveTimers.current.push(
      window.setTimeout(() => {
        ctrls.forEach((c) => c.stop())
        mx.set(hole.x)
        my.set(hole.y)
        mrx.set(hole.rx)
        mry.set(hole.ry)
        setCaptionReady(true)
      }, reduced ? 0 : MOVE_MS + 40),
    )
    return () => {
      moveTimers.current.forEach((t) => window.clearTimeout(t))
      moveTimers.current = []
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hole, reduced])

  // Keep the hole on its target if the window is resized mid-tour.
  useEffect(() => {
    const onResize = () => remeasure.current()
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const mask = useMotionTemplate`radial-gradient(${mrx}px ${mry}px at ${mx}px ${my}px, transparent 97%, rgba(0,0,0,1) 100%)`

  // Caption goes below the hole when it fits, above it when that fits, and
  // otherwise hugs the nearest edge so it never lands on top of the target.
  const captionStyle: CSSProperties = (() => {
    const vw = window.innerWidth
    const vh = window.innerHeight
    if (!hole) return { left: 16, top: 16 }
    const left = Math.round(Math.min(Math.max(16, hole.x - CAPTION_W / 2), Math.max(16, vw - CAPTION_W - 16)))
    const belowTop = hole.y + hole.ry + 16
    const aboveTop = hole.y - hole.ry - CAPTION_H - 16
    if (belowTop + CAPTION_H <= vh - 8) return { left, top: Math.round(Math.min(belowTop, vh - CAPTION_H - 8)) }
    if (aboveTop >= 8) return { left, top: Math.round(aboveTop) }
    return { left, top: Math.round(Math.max(8, vh - CAPTION_H - 8)) }
  })()

  const last = step === TOUR_STEPS.length - 1
  const s = TOUR_STEPS[step]

  return (
    <>
      <motion.div
        className="pointer-events-none fixed inset-0 z-[1200]"
        style={{
          background: 'rgba(33,30,26,0.62)',
          maskImage: mask,
          WebkitMaskImage: mask,
        }}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: reduced ? 0 : 0.3 }}
        aria-hidden="true"
      />

      <div className="fixed inset-0 z-[1201] pointer-events-none">
        <motion.div
          className="pointer-events-auto absolute w-[340px] border bg-panel p-4"
          style={{ ...captionStyle, borderColor: 'rgba(33,30,26,0.3)' }}
          initial={{ opacity: 0 }}
          animate={{ opacity: captionReady ? 1 : 0 }}
          transition={{ duration: reduced ? 0 : 0.3, ease: EASE }}
          role="dialog"
          aria-label={`Tour step ${step + 1} of ${TOUR_STEPS.length}: ${s?.title ?? ''}`}
        >
          <AnimatePresence mode="wait">
            {captionReady && s && (
              <motion.div
                key={step}
                initial={reduced ? { opacity: 0 } : { opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={reduced ? { opacity: 0 } : { opacity: 0, y: 10 }}
                transition={{ duration: reduced ? 0 : 0.35, ease: EASE }}
              >
                <p className="label">
                  {step + 1} / {TOUR_STEPS.length}
                </p>
                <h2 className="mt-1.5 font-display text-base font-bold leading-snug text-soot">{s.title}</h2>
                <p className="mt-1.5 text-xs leading-relaxed text-ash">{s.body}</p>
              </motion.div>
            )}
          </AnimatePresence>

          <div className="mt-4 flex items-center justify-between gap-2">
            <span className="flex items-center gap-1.5" aria-hidden="true">
              {TOUR_STEPS.map((t, idx) => (
                <span
                  key={t.target + idx}
                  className="h-[3px] w-4"
                  style={{ background: idx === step ? OCHRE : 'rgba(33,30,26,0.18)' }}
                />
              ))}
            </span>
            <span className="flex items-center gap-2">
              <button type="button" className="btn-quiet" onClick={onClose}>
                Exit tour
              </button>
              {step > 0 && (
                <button type="button" className="btn-quiet" onClick={() => setStep((p) => p - 1)}>
                  Back
                </button>
              )}
              <button type="button" className="btn-primary" onClick={() => (last ? onClose() : setStep((p) => p + 1))}>
                {last ? 'Finish' : 'Next'}
              </button>
            </span>
          </div>
        </motion.div>
      </div>
    </>
  )
}
