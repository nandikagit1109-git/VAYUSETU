import { useCallback, useEffect, useRef, useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { getFederatedStatus, runFederated } from '../api'
import type { FederatedStatus } from '../types'
import { RevealWords, SmokeRule } from '../motion'
import InfoAccordion from './InfoAccordion'

const POLL_MS = 2000
const TOTAL_ROUNDS = 8
const LINE_DRAW_MS = 900
// Convergence Pulse: local lines stagger 0.25s apart, then the shared global line
// waits 1.4s after the last local line before drawing in on top.
const STAGGER_MS = 250
const GLOBAL_WAIT_MS = 1400

// Series colours stay inside the warm family and are separated by lightness plus
// dash pattern. The three local lines render faint; the aggregated global line is
// the ember accent at full opacity and heavier stroke.
const SERIES = {
  Delhi: { stroke: '#b0763a', dash: undefined, width: 2, opacity: 0.45 },
  Kanpur: { stroke: '#6e5a46', dash: '6 3', width: 2, opacity: 0.45 },
  Pune: { stroke: '#a89880', dash: '2 3', width: 2, opacity: 0.45 },
  Global: { stroke: '#9e3b18', dash: undefined, width: 3.5, opacity: 1 },
} as const

const AXIS = { stroke: '#7c7367', tickFill: '#7c7367' }
const GRID = 'rgba(33, 30, 26, 0.10)'
const MONO = "'IBM Plex Mono', ui-monospace, monospace"

// "Actively monitoring" breath: inhale 4s, hold 4s, exhale 4s. Only while running.
function BreathingDot() {
  const reduced = useReducedMotion()
  return (
    <motion.span
      aria-hidden="true"
      className="inline-block h-2.5 w-2.5 rounded-full bg-ember"
      animate={reduced ? { scale: 1 } : { scale: [1, 1.4, 1.4, 1] }}
      transition={
        reduced
          ? { duration: 0 }
          : { duration: 12, times: [0, 4 / 12, 8 / 12, 1], repeat: Infinity, ease: 'easeInOut' }
      }
    />
  )
}

export default function FederatedPanel() {
  const reduced = useReducedMotion()
  const [status, setStatus] = useState<FederatedStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [starting, setStarting] = useState(false)
  const [seq, setSeq] = useState({ Delhi: false, Kanpur: false, Pune: false, Global: false })
  const seqStarted = useRef(false)
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

  const rounds = status?.rounds ?? []
  const done = rounds.length
  const running = status?.status === 'running'

  // Kick the Convergence Pulse sequence once the first round of a run lands.
  useEffect(() => {
    if (done === 0) {
      seqStarted.current = false
      setSeq({ Delhi: false, Kanpur: false, Pune: false, Global: false })
      return
    }
    if (seqStarted.current) return
    seqStarted.current = true
    // Reduced motion: no stagger, every series is on screen from the first round.
    if (reduced) {
      setSeq({ Delhi: true, Kanpur: true, Pune: true, Global: true })
      return
    }
    const timers = [
      window.setTimeout(() => setSeq((s) => ({ ...s, Delhi: true })), 0),
      window.setTimeout(() => setSeq((s) => ({ ...s, Kanpur: true })), STAGGER_MS),
      window.setTimeout(() => setSeq((s) => ({ ...s, Pune: true })), STAGGER_MS * 2),
      window.setTimeout(
        () => setSeq((s) => ({ ...s, Global: true })),
        STAGGER_MS * 2 + LINE_DRAW_MS + GLOBAL_WAIT_MS,
      ),
    ]
    return () => timers.forEach((t) => window.clearTimeout(t))
  }, [done, reduced])

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

  const chartData = rounds.map((r) => ({
    round: r.round,
    Delhi: r.client_losses.delhi,
    Kanpur: r.client_losses.kanpur,
    Pune: r.client_losses.pune,
    Global: r.global_loss,
  }))

  const dot = running ? <BreathingDot /> : (
    <span className={`inline-block h-2.5 w-2.5 rounded-full ${status?.status === 'completed' ? 'bg-ochre' : 'bg-ash'}`} aria-hidden="true" />
  )
  const statusLabel = running
    ? `Training, round ${done} of ${TOTAL_ROUNDS}`
    : status?.status === 'completed'
      ? `Completed, ${done} rounds`
      : 'Idle'

  return (
    <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
      <div className="panel flex flex-col p-5">
        <h2 className="font-display text-lg font-bold text-soot">Federated Learning</h2>
        <p className="measure mt-1 mb-4 text-xs leading-relaxed text-ash">
          Three city nodes (Delhi, Kanpur, Pune) train a shared next-hour AQI model with Flower FedAvg. Raw data never
          leaves a city; only model weight updates are aggregated. Runs {TOTAL_ROUNDS} rounds.
        </p>
        <button onClick={handleStart} disabled={starting || running} className="btn-primary w-full">
          {running ? 'Training in progress' : starting ? 'Starting…' : 'Start Federated Training'}
        </button>

        <div className="mt-4 flex items-center gap-2 text-sm">
          {dot}
          <span className="text-soot">{statusLabel}</span>
        </div>
        {status?.started_at && (
          <p className="tnum mt-2 text-xs text-ash">Started {new Date(status.started_at).toLocaleTimeString()}</p>
        )}
        {status?.completed_at && (
          <p className="tnum text-xs text-ash">Completed {new Date(status.completed_at).toLocaleTimeString()}</p>
        )}
        {error && <div className="banner-warn mt-3">{error}</div>}

        <div className="mt-4">
          <InfoAccordion title="What is federated learning?">
            <RevealWords text="Federated learning trains one shared model across the three city nodes without pooling their raw data. Each city fits the model on its own hourly AQI history and sends only weight updates to a central aggregator, which averages them with FedAvg and returns the improved shared weights. Raw observations never leave the city that collected them." />
          </InfoAccordion>
        </div>
      </div>

      <div className="panel p-5" data-tour="fed-chart">
        <h3 className="mb-2 font-display text-sm font-bold text-soot">
          Loss convergence · local per-city and aggregated global
        </h3>
        <SmokeRule className="mb-3" />
        <div className="h-[460px]">
          {done === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-1 px-6 text-center">
              <span className="text-sm text-soot">
                {running ? 'Waiting for round 1 to report in.' : 'No training run yet.'}
              </span>
              <span className="measure text-xs text-ash">
                {running
                  ? 'The chart fills in live as each round completes.'
                  : 'Press Start Federated Training and the loss curves below converge round by round.'}
              </span>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              {/* Chart stays mounted across polls; only its data prop updates, so the live fill is smooth (no flicker). */}
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
                  label={{ value: 'MSE loss', angle: -90, position: 'insideLeft', fill: AXIS.tickFill, fontSize: 11 }}
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
                <Legend wrapperStyle={{ fontSize: 12, color: '#211e1a' }} />
                {seq.Delhi && (
                  <Line type="monotone" dataKey="Delhi" stroke={SERIES.Delhi.stroke} strokeOpacity={SERIES.Delhi.opacity} strokeWidth={SERIES.Delhi.width} dot={{ r: 2.5, strokeWidth: 0 }} animationDuration={LINE_DRAW_MS} isAnimationActive={!reduced} />
                )}
                {seq.Kanpur && (
                  <Line type="monotone" dataKey="Kanpur" stroke={SERIES.Kanpur.stroke} strokeOpacity={SERIES.Kanpur.opacity} strokeWidth={SERIES.Kanpur.width} strokeDasharray={SERIES.Kanpur.dash} dot={{ r: 2.5, strokeWidth: 0 }} animationDuration={LINE_DRAW_MS} isAnimationActive={!reduced} />
                )}
                {seq.Pune && (
                  <Line type="monotone" dataKey="Pune" stroke={SERIES.Pune.stroke} strokeOpacity={SERIES.Pune.opacity} strokeWidth={SERIES.Pune.width} strokeDasharray={SERIES.Pune.dash} dot={{ r: 2.5, strokeWidth: 0 }} animationDuration={LINE_DRAW_MS} isAnimationActive={!reduced} />
                )}
                {seq.Global && (
                  <Line type="monotone" dataKey="Global" stroke={SERIES.Global.stroke} strokeOpacity={SERIES.Global.opacity} strokeWidth={SERIES.Global.width} dot={false} animationDuration={LINE_DRAW_MS} isAnimationActive={!reduced} />
                )}
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  )
}
