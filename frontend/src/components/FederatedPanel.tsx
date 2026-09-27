import { useCallback, useEffect, useRef, useState } from 'react'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { getFederatedStatus, runFederated } from '../api'
import type { FederatedStatus } from '../types'

const POLL_MS = 2000

export default function FederatedPanel() {
  const [status, setStatus] = useState<FederatedStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [starting, setStarting] = useState(false)
  const mounted = useRef(true)

  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])

  const refresh = useCallback(async () => {
    try {
      const s = await getFederatedStatus()
      if (mounted.current) setStatus(s)
    } catch (err) {
      // Transient polling errors must not spam the UI; keep last known state.
      console.warn('federated status poll failed:', err)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  // Poll every 2s only while a run is in progress.
  useEffect(() => {
    if (status?.status !== 'running') return
    const t = window.setInterval(refresh, POLL_MS)
    return () => window.clearInterval(t)
  }, [status?.status, refresh])

  async function handleStart() {
    setError(null)
    setStarting(true)
    try {
      await runFederated()
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not start training.')
    } finally {
      setStarting(false)
    }
  }

  const rounds = status?.rounds ?? []
  const chartData = rounds.map((r) => ({
    round: r.round,
    Delhi: r.client_losses.delhi,
    Kanpur: r.client_losses.kanpur,
    Pune: r.client_losses.pune,
    Global: r.global_loss,
  }))

  const statusLabel =
    status?.status === 'running'
      ? `Training… round ${rounds.length || 0}/8`
      : status?.status === 'completed'
        ? `Completed (${rounds.length} rounds)`
        : 'Idle'

  return (
    <div className="grid gap-4 lg:grid-cols-[340px_1fr]">
      <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
        <h2 className="mb-1 text-lg font-semibold">Federated Learning</h2>
        <p className="mb-4 text-xs leading-relaxed text-slate-400">
          Three city nodes (Delhi, Kanpur, Pune) train a shared next-hour AQI model with Flower FedAvg.
          Raw data never leaves a city — only model weight updates are aggregated. 8 rounds, ~30 seconds.
        </p>
        <button
          onClick={handleStart}
          disabled={starting || status?.status === 'running'}
          className="w-full rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {status?.status === 'running' ? 'Training in progress…' : starting ? 'Starting…' : 'Start Federated Training'}
        </button>
        <div className="mt-4 flex items-center gap-2 text-sm">
          <span
            className={`inline-block h-2.5 w-2.5 rounded-full ${
              status?.status === 'running'
                ? 'animate-pulse bg-amber-400'
                : status?.status === 'completed'
                  ? 'bg-emerald-400'
                  : 'bg-slate-500'
            }`}
          />
          <span className="text-slate-300">{statusLabel}</span>
        </div>
        {status?.started_at && (
          <p className="mt-2 text-xs text-slate-500">Started: {new Date(status.started_at).toLocaleTimeString()}</p>
        )}
        {status?.completed_at && (
          <p className="text-xs text-slate-500">Completed: {new Date(status.completed_at).toLocaleTimeString()}</p>
        )}
        {error && <div className="mt-3 rounded-lg border border-red-800 bg-red-950/60 px-3 py-2 text-xs text-red-300">{error}</div>}
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
        <h3 className="mb-3 text-sm font-semibold text-slate-200">Loss convergence (local per-city + aggregated global)</h3>
        <div className="h-[420px]">
          {rounds.length === 0 ? (
            <div className="flex h-full items-center justify-center text-sm text-slate-500">
              {status?.status === 'running' ? 'Waiting for the first round…' : 'Press “Start Federated Training” to begin.'}
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              {/* Chart stays mounted across polls — only its data prop updates (no flicker). */}
              <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="round" stroke="#64748b" tick={{ fontSize: 12 }} label={{ value: 'Round', position: 'insideBottomRight', offset: -4, fill: '#64748b', fontSize: 12 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 12 }} domain={[0, 'auto']} label={{ value: 'MSE loss', angle: -90, position: 'insideLeft', fill: '#64748b', fontSize: 12 }} />
                <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Line type="monotone" dataKey="Delhi" stroke="#f87171" strokeWidth={2} dot={{ r: 3 }} animationDuration={300} />
                <Line type="monotone" dataKey="Kanpur" stroke="#fbbf24" strokeWidth={2} dot={{ r: 3 }} animationDuration={300} />
                <Line type="monotone" dataKey="Pune" stroke="#34d399" strokeWidth={2} dot={{ r: 3 }} animationDuration={300} />
                <Line type="monotone" dataKey="Global" stroke="#38bdf8" strokeWidth={3} strokeDasharray="6 3" dot={false} animationDuration={300} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  )
}
