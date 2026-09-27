import { useCallback, useEffect, useState } from 'react'
import { acknowledgeAlert, checkAlerts, getAlerts } from '../api'
import type { Alert } from '../types'

const POLL_MS = 30000

const SEVERITY_STYLES: Record<string, string> = {
  Moderate: 'bg-yellow-500/15 text-yellow-300 border-yellow-500/40',
  Poor: 'bg-orange-500/15 text-orange-300 border-orange-500/40',
  'Very Poor': 'bg-red-500/15 text-red-300 border-red-500/40',
  Severe: 'bg-purple-500/15 text-purple-300 border-purple-500/40',
}

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
      // Update local state directly — no full refetch (per spec).
      setAlerts((prev) => prev.map((a) => (a.id === res.id ? { ...a, acknowledged: res.acknowledged } : a)))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Acknowledge failed.')
    } finally {
      setAckedBusy(null)
    }
  }

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <div className="mb-1 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Alerts & GRAP Recommendations</h2>
        <span className="text-xs text-slate-500">threshold check runs every 30s</span>
      </div>
      <p className="mb-4 text-xs text-slate-400">
        When a forecast crosses a GRAP threshold within 24h, an alert fires here with the matching graded-response action.
      </p>

      {error && <div className="mb-3 rounded-lg border border-red-800 bg-red-950/60 px-3 py-2 text-xs text-red-300">{error}</div>}

      {alerts.length === 0 ? (
        <div className="rounded-lg border border-slate-800 bg-slate-950/50 p-8 text-center text-sm text-slate-500">
          No alerts yet — the checker runs on load and every 30 seconds.
        </div>
      ) : (
        <ul className="space-y-3">
          {alerts.map((a) => (
            <li
              key={a.id}
              className={`rounded-lg border p-4 ${a.acknowledged ? 'border-slate-800 bg-slate-950/40 opacity-70' : 'border-slate-700 bg-slate-800/60'}`}
            >
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <span className={`rounded-full border px-2.5 py-0.5 text-xs font-semibold ${SEVERITY_STYLES[a.severity] ?? 'border-slate-600 bg-slate-700/30 text-slate-300'}`}>
                  {a.severity}
                </span>
                <span className="text-sm font-semibold capitalize text-slate-100">{a.city}</span>
                <span className="text-xs text-slate-400">predicted AQI {a.predicted_aqi.toFixed(0)}</span>
                <span className="rounded bg-slate-700/50 px-2 py-0.5 text-[10px] uppercase tracking-wide text-slate-300">
                  {CHANNEL_LABELS[a.channel] ?? a.channel}
                </span>
                <span className="ml-auto text-xs text-slate-500">
                  {a.created_at ? new Date(a.created_at).toLocaleString() : ''}
                </span>
              </div>
              <p className="mb-3 text-xs leading-relaxed text-slate-300">{a.grap_action}</p>
              {a.acknowledged ? (
                <span className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-400">
                  <span className="inline-block h-2 w-2 rounded-full bg-emerald-400" /> Acknowledged
                </span>
              ) : (
                <button
                  onClick={() => handleAcknowledge(a.id)}
                  disabled={ackedBusy === a.id}
                  className="rounded-lg bg-sky-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-sky-500 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {ackedBusy === a.id ? 'Acknowledging…' : 'Acknowledge'}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
