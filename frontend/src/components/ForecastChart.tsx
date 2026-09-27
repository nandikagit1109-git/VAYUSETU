import { useEffect, useState } from 'react'
import { useReducedMotion } from 'framer-motion'
import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { getForecast } from '../api'
import type { ForecastPointOut } from '../types'
import { FadeUp, SmokeRule } from '../motion'

const CITIES = [
  { value: 'delhi', label: 'Delhi' },
  { value: 'kanpur', label: 'Kanpur' },
  { value: 'pune', label: 'Pune' },
]

const AXIS = '#7c7367'
const GRID = 'rgba(33, 30, 26, 0.10)'
const MONO = "'IBM Plex Mono', ui-monospace, monospace"
const PREDICTED = '#9e3b18' // ember line: the forecast itself
const BAND = '#b0763a' // ochre band: the model's uncertainty
// Same draw-in length as the SmokePath strokes elsewhere, so the forecast line
// rhymes with the plume line and the wind vectors.
const LINE_DRAW_MS = 900

function timeLabel(iso: string): string {
  // "2026-08-30T13:00:00+00:00" -> "08-30 13h" (deterministic, locale-free)
  const m = iso.match(/^\d{4}-(\d{2}-\d{2})T(\d{2})/)
  return m ? `${m[1]} ${m[2]}h` : iso
}

export default function ForecastChart() {
  const reduced = useReducedMotion()
  const [city, setCity] = useState('delhi')
  const [points, setPoints] = useState<ForecastPointOut[] | null>(null)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const cityLabel = CITIES.find((c) => c.value === city)?.label ?? city

  useEffect(() => {
    let active = true
    setLoading(true)
    setError(null)
    setPending(false)
    getForecast(city)
      .then((res) => {
        if (!active) return
        if (res.error) {
          // Show our own specific pending copy rather than echoing the raw message.
          setPoints(null)
          setPending(true)
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
    <div className="panel p-5">
      <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-display text-lg font-bold text-soot">72-hour AQI forecast</h2>
          <p className="mt-1 text-xs text-ash">Per-city trained time-series model with an 80% confidence band.</p>
        </div>
        <div>
          <label className="label" htmlFor="forecast-city">
            City
          </label>
          <select id="forecast-city" value={city} onChange={(e) => setCity(e.target.value)} className="field w-40">
            {CITIES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <SmokeRule className="mb-4" />

      <div className="h-[340px]">
        {loading ? (
          <div className="flex h-full items-center justify-center text-sm text-ash">
            Fitting the {cityLabel} series and projecting 72 hours…
          </div>
        ) : error ? (
          <div className="flex h-full items-center justify-center px-6 text-center text-sm text-ember">{error}</div>
        ) : pending ? (
          <div className="flex h-full flex-col items-center justify-center gap-1 px-6 text-center">
            <span className="text-sm text-soot">Forecast pending for {cityLabel}.</span>
            <span className="measure text-xs text-ash">
              The time-series model for this city has not finished training yet.
            </span>
          </div>
        ) : chartData.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-ash">No forecast points available.</div>
        ) : (
          // Keyed on the city so switching cities re-enters with the same 18px drift
          // and the predicted line draws itself in again, left to right.
          <FadeUp key={city} className="h-full">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
                <XAxis dataKey="time" stroke={AXIS} tick={{ fontSize: 11, fill: AXIS, fontFamily: MONO }} minTickGap={48} />
                <YAxis
                  stroke={AXIS}
                  tick={{ fontSize: 11, fill: AXIS, fontFamily: MONO }}
                  domain={[0, 500]}
                  label={{ value: 'AQI', angle: -90, position: 'insideLeft', fill: AXIS, fontSize: 11 }}
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
                  formatter={(value) =>
                    Array.isArray(value) ? [`${value[0]} to ${value[1]}`, '80% band'] : [value, 'Predicted AQI']
                  }
                />
                <Area dataKey="band" stroke="none" fill={BAND} fillOpacity={0.16} isAnimationActive={false} />
                <Line
                  type="monotone"
                  dataKey="predicted"
                  stroke={PREDICTED}
                  strokeWidth={2.5}
                  dot={false}
                  animationDuration={LINE_DRAW_MS}
                  isAnimationActive={!reduced}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </FadeUp>
        )}
      </div>
    </div>
  )
}
