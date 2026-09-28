import type { City } from '../types'
import { aqiCategory, aqiColor, fmtAqi } from './AqiBadge'

interface Props {
  city: City | null
}

// Readout for the selected city on the Map & Report tab: latest ground AQI vs
// the citizen-blended adjusted AQI, plus tier and coverage labels.
export default function CityInfoCard({ city }: Props) {
  if (!city) {
    return (
      <div className="panel p-5">
        <h3 className="font-display text-sm font-bold text-soot">City readout</h3>
        <p className="mt-1 text-xs text-ash">Select a city marker on the map or in the search box.</p>
      </div>
    )
  }
  const tierLabel = city.tier === 1 ? 'ground monitoring' : city.tier === 2 ? 'weather/satellite only' : 'inferred (no data)'
  const blended = city.citizen_adjusted_aqi != null && city.latest_aqi != null && city.citizen_adjusted_aqi !== city.latest_aqi

  return (
    <div className="panel p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-display text-base font-bold text-soot">{city.name}</h3>
        <span className="text-[10px] uppercase tracking-[0.08em] text-ash">
          tier {city.tier} · {tierLabel}
        </span>
      </div>
      <p className="text-xs text-ash">{city.state}</p>

      <div className="mt-3 grid grid-cols-2 gap-3">
        <div className="rounded-sm border border-hairline bg-haze p-3">
          <span className="label mb-1">Latest AQI</span>
          <span className="tnum text-2xl font-semibold" style={{ color: city.latest_aqi == null ? undefined : aqiColor(city.latest_aqi) }}>
            {fmtAqi(city.latest_aqi)}
          </span>
          {city.latest_aqi != null && <span className="ml-1 text-xs text-ash">{aqiCategory(city.latest_aqi)}</span>}
          {city.latest_date && <p className="tnum mt-1 text-[10px] text-ash">{city.latest_date}</p>}
        </div>
        <div className="rounded-sm border border-hairline bg-haze p-3">
          <span className="label mb-1">Citizen-adjusted</span>
          <span className="tnum text-2xl font-semibold" style={{ color: city.citizen_adjusted_aqi == null ? undefined : aqiColor(city.citizen_adjusted_aqi) }}>
            {fmtAqi(city.citizen_adjusted_aqi)}
          </span>
          <p className="mt-1 text-[10px] text-ash">
            {city.report_count_24h > 0
              ? `${city.report_count_24h} report${city.report_count_24h === 1 ? '' : 's'} in 24h${blended ? ' · blended' : ''}`
              : 'no reports in 24h'}
          </p>
        </div>
      </div>
    </div>
  )
}
