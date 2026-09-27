import { useEffect, useState } from 'react'
import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { getForecast } from '../api'
import type { ForecastPointOut } from '../types'

const CITIES = [
  { value: 'delhi', label: 'Delhi' },
  { value: 'kanpur', label: 'Kanpur' },
  { value: 'pune', label: 'Pune' },
]

function timeLabel(iso: string): string {
  // "2026-08-30T13:00:00+00:00" -> "08-30 13h" (deterministic, locale-free)
  const m = iso.match(/^\d{4}-(\d{2}-\d{2})T(\d{2})/)
  return m ? `${m[1]} ${m[2]}h` : iso
}

export default function ForecastChart() {
  const [city, setCity] = useState('delhi')
  const [points, setPoints] = useState<ForecastPointOut[] | null>(null)
  const [pendingMessage, setPendingMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    setLoading(true)
    setError(null)
    setPendingMessage(null)
    getForecast(city)
      .then((res) => {
        if (!active) return
        if (res.error) {
          setPoints(null)
          setPendingMessage(res.message ?? 'Forecast pending — model not trained yet.')
        } else {
          setPoints(res.points ?? [])
        }
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : 'Could not load forecast.')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [city])

  const chartData = (points ?? []).map((p) => ({
    time: timeLabel(p.forecast_for),
    predicted: p.predicted_aqi,
    band: [p.lower_bound, p.upper_bound] as [number, number],
  }))

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">72-Hour AQI Forecast</h2>
          <p className="text-xs text-slate-400">Per-city trained time-series model with 80% confidence band.</p>
        </div>
        <select
          value={city}
          onChange={(e) => setCity(e.target.value)}
          className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none"
        >
          {CITIES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
      </div>

      <div className="h-[340px]">
        {loading ? (
          <div className="flex h-full items-center justify-center text-sm text-slate-500">Loading forecast…</div>
        ) : error ? (
          <div className="flex h-full items-center justify-center px-6 text-center text-sm text-red-300">{error}</div>
        ) : pendingMessage ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-sm text-slate-400">
            <span className="inline-block h-2.5 w-2.5 animate-pulse rounded-full bg-amber-400" />
            Forecast pending — {pendingMessage}
          </div>
        ) : chartData.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-slate-500">No forecast points available.</div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 11 }} minTickGap={48} />
              <YAxis stroke="#64748b" tick={{ fontSize: 12 }} domain={[0, 500]} label={{ value: 'AQI', angle: -90, position: 'insideLeft', fill: '#64748b', fontSize: 12 }} />
              <Tooltip
                contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }}
                formatter={(value) => (Array.isArray(value) ? [`${value[0]} – ${value[1]}`, '80% band'] : [value, 'Predicted AQI'])}
              />
              <Area dataKey="band" stroke="none" fill="#475569" fillOpacity={0.45} isAnimationActive={false} />
              <Line type="monotone" dataKey="predicted" stroke="#38bdf8" strokeWidth={2.5} dot={false} animationDuration={300} />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}
