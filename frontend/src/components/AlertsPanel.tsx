import { useCallback, useEffect, useState } from 'react'
import { acknowledgeAlert, checkAlerts, getAlerts } from '../api'
import type { Alert } from '../types'

const POLL_MS = 30000

// Solid severity chips keyed to the warm AQI ramp; foreground flips to the light
// panel colour once the fill gets dark enough to need it.
const SEVERITY_CHIP: Record<string, { bg: string; fg: string }> = {
  Moderate: { bg: '#c6b184', fg: '#211e1a' },
  Poor: { bg: '#c08a3e', fg: '#211e1a' },
  'Very Poor': { bg: '#b0552a', fg: '#f2eee6' },
  Severe: { bg: '#7e2d14', fg: '#f2eee6' },
}

// Rank used to order the list by real urgency (worst first), not just recency.
const SEVERITY_RANK: Record<string, number> = { Severe: 4, 'Very Poor': 3, Poor: 2, Moderate: 1 }

const CHANNEL_LABELS: Record<string, string> = {
  dashboard: 'Dashboard',
  sms_simulated: 'SMS (simulated)',
  whatsapp_simulated: 'WhatsApp (simulated)',
}

export default function AlertsPanel() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [error, setError] = useState<string | null>(null)
  const [ackedBusy, setAckedBusy] = useState<number | null>(null)

  const refresh = useCallback(async () => {
    try {
      // Fire the threshold check first (per spec: on load + every 30s), then fetch.
      await checkAlerts().catch((err) => console.warn('alert check failed:', err))
      const data = await getAlerts()
      setAlerts(data.alerts ?? [])
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load alerts.')
    }
  }, [])

  useEffect(() => {
    refresh()
    const t = window.setInterval(refresh, POLL_MS)
    return () => window.clearInterval(t)
  }, [refresh])

  async function handleAcknowledge(id: number) {
    setAckedBusy(id)
    try {
      const res = await acknowledgeAlert(id)
      // Update local state directly; no full refetch (per spec).
      setAlerts((prev) => prev.map((a) => (a.id === res.id ? { ...a, acknowledged: res.acknowledged } : a)))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Acknowledge failed.')
    } finally {
      setAckedBusy(null)
    }
  }

  // Unacknowledged first, then worst severity, then newest. ISO timestamps sort
  // lexicographically, so string compare is chronological.
  const ordered = [...alerts].sort((a, b) => {
    if (a.acknowledged !== b.acknowledged) return a.acknowledged ? 1 : -1
    const rank = (SEVERITY_RANK[b.severity] ?? 0) - (SEVERITY_RANK[a.severity] ?? 0)
    if (rank !== 0) return rank
    return (b.created_at ?? '').localeCompare(a.created_at ?? '')
  })

  return (
    <div className="panel p-5">
      <div className="mb-1 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-display text-lg font-bold text-soot">Alerts and GRAP recommendations</h2>
        <span className="text-xs text-ash">threshold check runs every 30s</span>
      </div>
      <p className="measure mb-4 text-xs leading-relaxed text-ash">
        When a forecast crosses a GRAP threshold within 24 hours, an alert appears here with the matching graded
        response action.
      </p>

      {error && <div className="banner-warn mb-3">{error}</div>}

      {ordered.length === 0 ? (
        <div className="rounded-sm border border-hairline bg-haze px-4 py-8 text-center">
          <p className="text-sm text-soot">No alerts right now.</p>
          <p className="measure mx-auto mt-1 text-xs text-ash">
            The threshold checker runs on load and every 30 seconds. Alerts appear here when a city forecast crosses a
            GRAP stage within the next 24 hours.
          </p>
        </div>
      ) : (
        <ul className="divide-y divide-hairline">
          {ordered.map((a) => {
            const chip = SEVERITY_CHIP[a.severity] ?? { bg: '#7c7367', fg: '#f2eee6' }
            return (
              <li key={a.id} className={`py-4 first:pt-1 last:pb-1 ${a.acknowledged ? 'opacity-60' : ''}`}>
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <span
                    className="rounded-sm px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide"
                    style={{ background: chip.bg, color: chip.fg }}
                  >
                    {a.severity}
                  </span>
                  <span className="font-display text-sm font-bold capitalize text-soot">{a.city}</span>
                  <span className="text-xs text-ash">
                    predicted AQI <span className="tnum font-medium text-soot">{a.predicted_aqi.toFixed(0)}</span>
                  </span>
                  <span className="rounded-sm border border-hairline bg-haze px-2 py-0.5 text-[10px] uppercase tracking-wide text-ash">
                    {CHANNEL_LABELS[a.channel] ?? a.channel}
                  </span>
                  <span className="tnum ml-auto text-xs text-ash">
                    {a.created_at ? new Date(a.created_at).toLocaleString() : ''}
                  </span>
                </div>

                <p className="measure mb-3 text-sm leading-relaxed text-soot">{a.grap_action}</p>

                {a.acknowledged ? (
                  <span className="inline-flex items-center gap-1.5 text-xs font-medium text-ash">
                    <span className="inline-block h-2 w-2 rounded-full bg-ochre" aria-hidden="true" />
                    Acknowledged
                  </span>
                ) : (
                  <button onClick={() => handleAcknowledge(a.id)} disabled={ackedBusy === a.id} className="btn-quiet">
                    {ackedBusy === a.id ? 'Acknowledging…' : 'Acknowledge'}
                  </button>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
