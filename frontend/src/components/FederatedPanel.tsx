import { useCallback, useEffect, useRef, useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { getFederatedEval, getFederatedStatus, runFederated } from '../api'
import type { FlEval, FlStatus } from '../types'
import { RevealWords, SmokeRule } from '../motion'
import InfoAccordion from './InfoAccordion'

const POLL_MS = 2000
const LINE_DRAW_MS = 900
const GLOBAL_WAIT_MS = 1400

// Series colours stay inside the warm family, separated by lightness and dash.
// The global line is the ember accent; local lines are faint warm greys.
const LOCAL_STROKES = ['#b0763a', '#6e5a46', '#a89880', '#8a6a4a', '#b59a7d', '#7c6a55', '#9c8570', '#6e5a46']
const GLOBAL = { stroke: '#9e3b18', width: 3.5 }

const AXIS = { stroke: '#7c7367', tickFill: '#7c7367' }
const GRID = 'rgba(33, 30, 26, 0.10)'
const MONO = "'IBM Plex Mono', ui-monospace, monospace"

function seriesFor(clientId: string, index: number) {
  return {
    stroke: LOCAL_STROKES[index % LOCAL_STROKES.length],
    dash: index % 3 === 1 ? '6 3' : index % 3 === 2 ? '2 3' : undefined,
    width: 2,
    opacity: 0.45,
    label: clientId,
  }
}

// "Actively monitoring" breath: only while a run is in progress.
function BreathingDot() {
  const reduced = useReducedMotion()
  return (
    <motion.span
      aria-hidden="true"
      className="inline-block h-2.5 w-2.5 rounded-full bg-ember"
      animate={reduced ? { scale: 1 } : { scale: [1, 1.4, 1.4, 1] }}
      transition={reduced ? { duration: 0 } : { duration: 12, times: [0, 4 / 12, 8 / 12, 1], repeat: Infinity, ease: 'easeInOut' }}
    />
  )
}

export default function FederatedPanel() {
  const reduced = useReducedMotion()
  const [status, setStatus] = useState<FlStatus | null>(null)
  const [evalData, setEvalData] = useState<FlEval | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [starting, setStarting] = useState(false)
  // Which per-city lines have revealed (Convergence Pulse). Dynamic cohort, so
  // the set is driven by status.clients.
  const [revealed, setRevealed] = useState<Record<string, boolean>>({})
  const [globalRevealed, setGlobalRevealed] = useState(false)
  const seqStarted = useRef(false)
  const seqKey = useRef(0)
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
      if (!mounted.current) return
      setStatus(s)
      setError(null)
      if (s.status === 'completed') {
        getFederatedEval()
          .then((e) => {
            if (mounted.current) setEvalData(e)
          })
          .catch(() => undefined)
      }
    } catch (err) {
      // Transient polling errors must not spam the UI; keep last known state.
      console.warn('federated status poll failed:', err)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  // Poll every 2s while running (interval always cleared on unmount).
  useEffect(() => {
    if (status?.status !== 'running') return
    const t = window.setInterval(refresh, POLL_MS)
    return () => window.clearInterval(t)
  }, [status?.status, refresh])

  const rounds = status?.rounds ?? []
  const done = rounds.length
  const running = status?.status === 'running'
  const clients = status?.clients ?? []

  // Convergence Pulse with the v2 override (section 13): stagger is
  // min(0.25, 2.0 / n_clients) seconds so the reveal finishes in ~2s no matter
  // how many cities train; the global line draws 1.4s after the last local
  // line BEGINS.
  useEffect(() => {
    if (done === 0) {
      seqStarted.current = false
      setRevealed({})
      setGlobalRevealed(false)
      return
    }
    if (seqStarted.current) return
    seqStarted.current = true
    seqKey.current += 1
    if (reduced) {
      setRevealed(Object.fromEntries(clients.map((c) => [c, true])))
      setGlobalRevealed(true)
      return
    }
    const n = Math.max(1, clients.length)
    const staggerMs = Math.min(250, (2.0 / n) * 1000)
    const timers: number[] = []
    clients.forEach((c, i) => {
      timers.push(window.setTimeout(() => setRevealed((r) => ({ ...r, [c]: true })), i * staggerMs))
    })
    const lastBegin = (clients.length - 1) * staggerMs
    timers.push(window.setTimeout(() => setGlobalRevealed(true), lastBegin + GLOBAL_WAIT_MS))
    return () => timers.forEach((t) => window.clearTimeout(t))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [done === 0, clients.join(','), reduced])

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

  const chartData = rounds.map((r) => {
    const row: Record<string, number | null> = { round: r.round, Global: r.global_loss }
    for (const c of clients) {
      const v = r.client_losses[c]
      row[c] = typeof v === 'number' ? v : null
    }
    return row
  })

  const dot = running ? <BreathingDot /> : (
    <span className={`inline-block h-2.5 w-2.5 rounded-full ${status?.status === 'completed' ? 'bg-ochre' : status?.status === 'failed' ? 'bg-ember' : 'bg-ash'}`} aria-hidden="true" />
  )
  const statusLabel = running
    ? `Training, round ${done} of ${status?.total_rounds ?? 8}`
    : status?.status === 'completed'
      ? `Completed, ${done} rounds`
      : status?.status === 'failed'
        ? 'Run failed'
        : 'Idle'

  return (
    <div className="grid gap-4 lg:grid-cols-[340px_1fr]">
      <div className="flex flex-col gap-4">
        <div className="panel p-5">
          <h2 className="font-display text-lg font-bold text-soot">Federated Learning</h2>
          <p className="measure mt-1 mb-4 text-xs leading-relaxed text-ash">
            Every tier-1 city with enough history joins the round: each node trains on its own daily records and
            sends <strong>only model weights</strong> to the averager. Raw data never leaves a city. {status?.total_rounds ?? 8} rounds,
            all {clients.length} participating cities.
          </p>
          <button onClick={handleStart} disabled={starting || running} className="btn-primary w-full">
            {running ? 'Training in progress' : starting ? 'Starting…' : 'Start federated training'}
          </button>

          <div className="mt-4 flex items-center gap-2 text-sm">
            {dot}
            <span className="text-soot">{statusLabel}</span>
          </div>
          {status?.started_at && <p className="tnum mt-2 text-xs text-ash">Started {new Date(status.started_at).toLocaleTimeString()}</p>}
          {status?.completed_at && <p className="tnum text-xs text-ash">Completed {new Date(status.completed_at).toLocaleTimeString()}</p>}
          {status?.error && <div className="banner-warn mt-3">{status.error}</div>}
          {error && <div className="banner-warn mt-3">{error}</div>}

          <div className="mt-4">
            <InfoAccordion title="What crosses the city boundary?">
              <RevealWords text="Only three things ever leave a city: the model parameter arrays, the number of training samples, and scalar loss numbers. No raw measurements, no daily records, no per-row data. The server averages the weighted parameters and broadcasts the shared model back." />
            </InfoAccordion>
          </div>
        </div>

        {status && status.excluded.length > 0 && (
          <div className="panel p-5">
            <h3 className="font-display text-sm font-bold text-soot">Excluded cities</h3>
            <p className="mt-1 text-xs text-ash">Tier-1 cities without enough training windows this run.</p>
            <ul className="mt-2 space-y-1 text-xs">
              {status.excluded.map((e) => (
                <li key={e.city_id} className="flex items-baseline justify-between gap-2">
                  <span className="font-medium text-soot">{e.city_id}</span>
                  <span className="text-ash">{e.reason}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {evalData?.available && (
          <div className="panel p-5" data-tour="fed-eval">
            <h3 className="font-display text-sm font-bold text-soot">Did federation help?</h3>
            <p className="mt-1 mb-3 text-xs leading-relaxed text-ash">
              Validation MAE (AQI points) per city, reported exactly as measured: persistence baseline, local-only
              training, the shared federated model, and the federated model after a light per-city fine-tune
              (personalized).
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-hairline text-left text-ash">
                    <th className="py-1.5 pr-2 font-medium">City</th>
                    <th className="py-1.5 px-2 text-right font-medium">Persist.</th>
                    <th className="py-1.5 px-2 text-right font-medium">Local</th>
                    <th className="py-1.5 px-2 text-right font-medium">Federated</th>
                    <th className="py-1.5 px-2 text-right font-medium">Personalized</th>
                  </tr>
                </thead>
                <tbody className="tnum">
                  {evalData.rows.map((r) => (
                    <tr key={r.city_id} className="border-b border-hairline/60">
                      <td className="py-1.5 pr-2 font-medium text-soot">{r.name}</td>
                      <td className="py-1.5 px-2 text-right">{r.mae_persistence.toFixed(1)}</td>
                      <td className="py-1.5 px-2 text-right">{r.mae_local.toFixed(1)}</td>
                      <td className={`py-1.5 px-2 text-right font-semibold ${r.mae_federated <= Math.min(r.mae_persistence, r.mae_local) ? 'text-ochre' : ''}`}>
                        {r.mae_federated.toFixed(1)}
                      </td>
                      <td className="py-1.5 px-2 text-right">{r.mae_personalized.toFixed(1)}</td>
                    </tr>
                  ))}
                  <tr className="font-semibold text-soot">
                    <td className="py-1.5 pr-2">Mean</td>
                    <td className="py-1.5 px-2 text-right">{evalData.mean_mae_persistence?.toFixed(1) ?? '—'}</td>
                    <td className="py-1.5 px-2 text-right">{evalData.mean_mae_local?.toFixed(1) ?? '—'}</td>
                    <td className="py-1.5 px-2 text-right">{evalData.mean_mae_federated?.toFixed(1) ?? '—'}</td>
                    <td className="py-1.5 px-2 text-right">{evalData.mean_mae_personalized?.toFixed(1) ?? '—'}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      <div className="panel p-5" data-tour="fed-chart">
        <h3 className="mb-2 font-display text-sm font-bold text-soot">
          Loss convergence · local per-city and aggregated global
        </h3>
        <SmokeRule className="mb-3" />
        <div className="h-[460px]">
          {done === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-1 px-6 text-center">
              <span className="text-sm text-soot">{running ? 'Waiting for round 1 to report in.' : 'No training run yet.'}</span>
              <span className="measure text-xs text-ash">
                {running
                  ? 'The chart fills in live as each round completes.'
                  : 'Press Start federated training and the loss curves below converge round by round.'}
              </span>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              {/* Chart stays mounted across polls; only its data prop updates. */}
              <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
                <XAxis
                  dataKey="round"
                  stroke={AXIS.stroke}
                  tick={{ fontSize: 11, fill: AXIS.tickFill, fontFamily: MONO }}
                  label={{ value: 'Round', position: 'insideBottomRight', offset: -4, fill: AXIS.tickFill, fontSize: 11 }}
                />
                <YAxis
                  stroke={AXIS.stroke}
                  tick={{ fontSize: 11, fill: AXIS.tickFill, fontFamily: MONO }}
                  domain={[0, 'auto']}
                  label={{ value: 'Train loss (MSE, scaled)', angle: -90, position: 'insideLeft', fill: AXIS.tickFill, fontSize: 11 }}
                />
                <Tooltip
                  contentStyle={{
                    background: '#f2eee6',
                    border: '1px solid rgba(33,30,26,0.3)',
                    borderRadius: 3,
                    fontSize: 12,
                    color: '#211e1a',
                    boxShadow: 'none',
                  }}
                  labelFormatter={(v) => `Round ${v}`}
                />
                <Legend wrapperStyle={{ fontSize: 11, color: '#211e1a' }} />
                {clients.map((c, i) => {
                  const s = seriesFor(c, i)
                  return revealed[c] ? (
                    <Line
                      key={`${seqKey}-${c}`}
                      type="monotone"
                      dataKey={c}
                      stroke={s.stroke}
                      strokeOpacity={s.opacity}
                      strokeWidth={s.width}
                      strokeDasharray={s.dash}
                      dot={false}
                      animationDuration={LINE_DRAW_MS}
                      isAnimationActive={!reduced}
                      name={c}
                    />
                  ) : null
                })}
                {globalRevealed && (
                  <Line
                    key={`${seqKey}-global`}
                    type="monotone"
                    dataKey="Global"
                    stroke={GLOBAL.stroke}
                    strokeWidth={GLOBAL.width}
                    dot={false}
                    animationDuration={LINE_DRAW_MS}
                    isAnimationActive={!reduced}
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  )
}
