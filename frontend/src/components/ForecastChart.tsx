import { useEffect, useMemo, useState } from 'react'
import { useReducedMotion } from 'framer-motion'
import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { getCityHistory, getForecast } from '../api'
import type { ApiError, City, CityHistoryPoint, Forecast } from '../types'
import { FadeUp, SmokeRule } from '../motion'
import CitySearch from './CitySearch'

const AXIS = '#7c7367'
const GRID = 'rgba(33, 30, 26, 0.10)'
const MONO = "'IBM Plex Mono', ui-monospace, monospace"
const PREDICTED = '#9e3b18' // ember: the forecast line
const BAND = '#b0763a' // ochre: the uncertainty band
const HISTORY = '#7c7367' // ash: observed history line
const OBSERVED_DOT = '#211e1a'
const LINE_DRAW_MS = 900

const METHOD_LABEL: Record<Forecast['method'], string> = {
  federated_gru: 'federated model',
  persistence: 'persistence baseline',
  neighbor_idw: 'interpolated from nearby cities',
}

interface Row {
  label: string
  aqi: number | null
  band: [number, number] | null
  observed: boolean
}

function isApiError(x: Forecast | ApiError): x is ApiError {
  return (x as ApiError).error === true
}

interface Props {
  cities: City[]
  selectedCityId?: string
  onSelectCity?: (cityId: string) => void
}

export default function ForecastChart({ cities, selectedCityId, onSelectCity }: Props) {
  const reduced = useReducedMotion()
  const [internalCityId, setInternalCityId] = useState<string>(selectedCityId ?? cities[0]?.city_id ?? 'delhi')
  const cityId = selectedCityId ?? internalCityId
  const setCityId = (id: string) => {
    setInternalCityId(id)
    onSelectCity?.(id)
  }
  const [history, setHistory] = useState<CityHistoryPoint[]>([])
  const [forecast, setForecast] = useState<Forecast | null>(null)
  const [pending, setPending] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const city = useMemo(() => cities.find((c) => c.city_id === cityId) ?? null, [cities, cityId])

  useEffect(() => {
    if (!cityId) return
    let active = true
    setLoading(true)
    setError(null)
    setPending(null)
    setForecast(null)
    setHistory([])
    Promise.all([
      getCityHistory(cityId, 30).catch((err) => {
        if (active) setError(err instanceof Error ? err.message : 'Could not load history.')
        return { points: [] as CityHistoryPoint[] }
      }),
      getForecast(cityId),
    ])
      .then(([hist, fc]) => {
        if (!active) return
        setHistory(hist.points ?? [])
        if (isApiError(fc)) {
          setPending(fc.message)
        } else {
          setForecast(fc)
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
  }, [cityId])

  const chartData = useMemo<Row[]>(() => {
    const rows: Row[] = history.map((h) => ({
      label: h.date.slice(5),
      aqi: h.aqi,
      band: null,
      observed: true,
    }))
    for (const p of forecast?.points ?? []) {
      // The observed point (horizon 0) is already the last history day; adding
      // it again would duplicate the row key (console error in Recharts).
      if (p.observed && history.length > 0 && history[history.length - 1].date === p.date) {
        continue
      }
      rows.push({
        label: p.date.slice(5),
        aqi: p.predicted_aqi,
        band: [p.lower_bound, p.upper_bound],
        observed: p.observed,
      })
    }
    return rows
  }, [history, forecast])

  const method = forecast?.method
  const historySpan = history.length

  return (
    <div className="panel p-5">
      <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-display text-lg font-bold text-soot">AQI forecast</h2>
          <p className="mt-1 text-xs text-ash">
            30-day history then +1/+2/+3 day forecast, with the uncertainty band.
            {method && (
              <>
                {' '}Method: <span className="font-semibold text-soot">{METHOD_LABEL[method]}</span>.
              </>
            )}
          </p>
        </div>
        <div className="w-64">
          <CitySearch cities={cities} value={cityId} onChange={setCityId} id="forecast-city" />
        </div>
      </div>

      <SmokeRule className="mb-4" />

      <div className="h-[340px]">
        {loading ? (
          <div className="flex h-full items-center justify-center text-sm text-ash">Loading {city?.name ?? 'city'}…</div>
        ) : error ? (
          <div className="flex h-full items-center justify-center px-6 text-center text-sm text-ember">{error}</div>
        ) : pending ? (
          <div className="flex h-full flex-col items-center justify-center gap-1 px-6 text-center">
            <span className="text-sm text-soot">No forecast available for {city?.name}.</span>
            <span className="measure text-xs text-ash">{pending}</span>
          </div>
        ) : chartData.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-ash">No data for this city yet.</div>
        ) : (
          <FadeUp key={cityId} className="h-full">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
                <XAxis dataKey="label" stroke={AXIS} tick={{ fontSize: 11, fill: AXIS, fontFamily: MONO }} minTickGap={40} />
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
                  formatter={(value, name) =>
                    Array.isArray(value) ? [`${value[0]} – ${value[1]}`, 'band'] : [value, name === 'aqi' ? 'AQI' : name]
                  }
                />
                {/* Uncertainty band (forecast points only; null elsewhere). */}
                <Area dataKey="band" stroke="none" fill={BAND} fillOpacity={0.16} isAnimationActive={false} connectNulls />
                {/* History drawn before the forecast, in quiet ash. */}
                <Line
                  type="monotone"
                  dataKey="aqi"
                  stroke={HISTORY}
                  strokeWidth={1.6}
                  strokeDasharray="4 4"
                  dot={false}
                  isAnimationActive={false}
                  connectNulls
                />
                {/* Forecast line: same data key, ember, drawn over the tail. */}
                <Line
                  type="monotone"
                  dataKey="aqi"
                  stroke={PREDICTED}
                  strokeWidth={2.5}
                  dot={(props: { cx?: number; cy?: number; payload?: Row }) => {
                    const { cx, cy, payload } = props
                    if (!payload?.observed || payload.aqi == null || cx == null || cy == null) return <g key={`d-${payload?.label}`} />
                    return <circle key={`obs-${payload.label}`} cx={cx} cy={cy} r={4} fill={OBSERVED_DOT} stroke="#f2eee6" strokeWidth={1.5} />
                  }}
                  animationDuration={LINE_DRAW_MS}
                  isAnimationActive={!reduced}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </FadeUp>
        )}
      </div>
      {historySpan === 0 && !loading && !error && (
        <p className="mt-2 text-xs text-ash">No observed history for this city — the forecast starts from neighbour interpolation.</p>
      )}
    </div>
  )
}
