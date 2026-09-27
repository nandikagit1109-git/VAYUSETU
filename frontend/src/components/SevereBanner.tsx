import { useEffect, useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { checkAlerts, getAlerts } from '../api'
import type { Alert } from '../types'
import { EASE } from '../motion'
import { cityLabel } from '../cities'

const POLL_MS = 30000

const SEVERITY_RANK: Record<string, number> = { Severe: 0, 'Very Poor': 1, Poor: 2, Moderate: 3 }

const SEVERITY_INK: Record<string, string> = {
  Moderate: 'var(--sev-moderate)',
  Poor: 'var(--sev-poor)',
  'Very Poor': 'var(--sev-very-poor)',
  Severe: 'var(--sev-severe)',
}

// GRAP Stage III and IV are the ones that close schools or stop trucks; those are
// the only alerts worth interrupting another tab for.
const BANNER_SEVERITIES = new Set(['Very Poor', 'Severe'])

interface SevereBannerProps {
  suppressed: boolean
  onView: () => void
}

// Sticky banner for the most urgent unacknowledged GRAP Stage-II+ alert. It stays
// down while the Alerts tab, the intro or the tour owns the screen, and slides up
// otherwise; View jumps to Alerts, Dismiss hides that alert id for the session.
export default function SevereBanner({ suppressed, onView }: SevereBannerProps) {
  const reduced = useReducedMotion()
  const [worst, setWorst] = useState<Alert | null>(null)
  const [dismissed, setDismissed] = useState<number[]>([])

  useEffect(() => {
    // On the Alerts tab that panel owns the threshold check and the list; stay quiet here.
    if (suppressed) return
    let live = true
    const load = async () => {
      try {
        await checkAlerts().catch(() => undefined)
        const data = await getAlerts()
        if (!live) return
        const candidates = (data.alerts ?? [])
          .filter((a) => !a.acknowledged && BANNER_SEVERITIES.has(a.severity) && !dismissed.includes(a.id))
          .sort((a, b) => {
            const rank = (SEVERITY_RANK[a.severity] ?? 9) - (SEVERITY_RANK[b.severity] ?? 9)
            if (rank !== 0) return rank
            return (b.created_at ?? '').localeCompare(a.created_at ?? '')
          })
        setWorst(candidates[0] ?? null)
      } catch {
        // The dashboard still works without the banner; the Alerts tab reports errors.
      }
    }
    load()
    const t = window.setInterval(load, POLL_MS)
    return () => {
      live = false
      window.clearInterval(t)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [suppressed])

  const visible = Boolean(worst) && !suppressed

  return (
    <motion.div
      className="pointer-events-none fixed inset-x-0 bottom-0 z-[1150] flex justify-center px-4 pb-4"
      initial={false}
      animate={{ y: visible ? 0 : '130%' }}
      transition={reduced ? { duration: 0 } : { duration: 0.5, ease: EASE }}
      aria-live="polite"
    >
      {worst && (
        <div
          className="pointer-events-auto flex w-full max-w-3xl flex-wrap items-center gap-x-4 gap-y-2 border bg-panel px-4 py-3"
          style={{ borderColor: SEVERITY_INK[worst.severity] ?? 'var(--hairline-strong)' }}
        >
          <span
            className="inline-block h-2.5 w-2.5 shrink-0 rounded-full"
            style={{ background: SEVERITY_INK[worst.severity] ?? 'var(--ember)' }}
            aria-hidden="true"
          />
          <p className="min-w-0 flex-1 text-xs leading-relaxed text-soot">
            <span className="font-semibold">
              {worst.severity} alert for {cityLabel(worst.city)}
            </span>
            <span className="text-ash">
              {' '}
              · predicted AQI <span className="tnum">{worst.predicted_aqi.toFixed(0)}</span>.{' '}
            </span>
            <span className="line-clamp-2 text-ash">{worst.grap_action}</span>
          </p>
          <span className="ml-auto flex items-center gap-2">
            <button type="button" className="btn-primary py-1.5" onClick={onView}>
              View
            </button>
            <button
              type="button"
              className="btn-quiet py-1.5"
              onClick={() => {
                setDismissed((d) => [...d, worst.id])
                setWorst(null)
              }}
            >
              Dismiss
            </button>
          </span>
        </div>
      )}
    </motion.div>
  )
}
