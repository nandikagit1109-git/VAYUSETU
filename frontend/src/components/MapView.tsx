import { CircleMarker, MapContainer, TileLayer, Tooltip, useMapEvents } from 'react-leaflet'
import type { City, CitizenReport } from '../types'
import { aqiColor } from './AqiBadge'

const SOOT = '#211e1a'
const PANEL = '#f2eee6'
const OCHRE = '#b0763a'

// India-wide bounds (map is national now, not fitted to the city table, so a
// lone Andaman report cannot zoom the view out).
export const INDIA_BOUNDS: [[number, number], [number, number]] = [
  [6.5, 68.0],
  [37.0, 97.0],
]

// Tier is encoded by STROKE STYLE, not hue (design constraint):
//   tier 1 filled ochre, tier 2 ring, tier 3 dashed ring.
function cityPathOptions(tier: 1 | 2 | 3) {
  if (tier === 1) return { color: SOOT, weight: 1.6, fillColor: OCHRE, fillOpacity: 1 }
  if (tier === 2) return { color: SOOT, weight: 2, fillColor: PANEL, fillOpacity: 0.85 }
  return { color: SOOT, weight: 1.6, dashArray: '3 3', fillColor: PANEL, fillOpacity: 0.6 }
}

// Marker radius scales with the latest AQI (or citizen-adjusted AQI).
function cityRadius(aqi: number | null): number {
  if (aqi == null) return 4
  return 4 + Math.min(6, (aqi / 500) * 10)
}

function ClickHandler({ onPick }: { onPick: (lat: number, lon: number) => void }) {
  useMapEvents({
    click(e) {
      onPick(e.latlng.lat, e.latlng.lng)
    },
  })
  return null
}

interface Props {
  cities: City[]
  reports: CitizenReport[]
  selectedCityId: string | null
  onSelectCity: (cityId: string) => void
  onMapPick?: (lat: number, lon: number) => void
}

export default function MapView({ cities, reports, selectedCityId, onSelectCity, onMapPick }: Props) {
  return (
    <MapContainer bounds={INDIA_BOUNDS} boundsOptions={{ padding: [18, 18] }} scrollWheelZoom style={{ height: '100%', width: '100%' }}>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {onMapPick && <ClickHandler onPick={onMapPick} />}

      {cities.map((c) => {
        const selected = c.city_id === selectedCityId
        const aqi = c.citizen_adjusted_aqi ?? c.latest_aqi
        return (
          <CircleMarker
            key={c.city_id}
            center={[c.latitude, c.longitude]}
            radius={selected ? cityRadius(aqi) + 2 : cityRadius(aqi)}
            pathOptions={{
              ...cityPathOptions(c.tier),
              ...(selected ? { color: '#9e3b18', weight: 2.5 } : {}),
            }}
            eventHandlers={{ click: () => onSelectCity(c.city_id) }}
          >
            <Tooltip className="vayu-tooltip" direction="top">
              <div className="font-semibold">{c.name}</div>
              <div>
                Tier {c.tier} ·{' '}
                {c.tier === 1 ? 'ground monitoring' : c.tier === 2 ? 'weather/satellite only' : 'inferred from neighbours'}
              </div>
              <div>
                Latest AQI <span className="tnum">{c.latest_aqi?.toFixed(0) ?? '—'}</span>
                {c.citizen_adjusted_aqi != null && (
                  <>
                    {' '}· citizen-adjusted <span className="tnum">{c.citizen_adjusted_aqi.toFixed(0)}</span>
                  </>
                )}
              </div>
            </Tooltip>
          </CircleMarker>
        )
      })}

      {reports.map((r) => (
        <CircleMarker
          key={r.id}
          center={[r.latitude, r.longitude]}
          radius={5}
          pathOptions={{ color: SOOT, weight: 1, fillColor: aqiColor(r.haze_score), fillOpacity: 1 }}
        >
          <Tooltip className="vayu-tooltip" direction="top">
            <div className="font-semibold">
              Citizen report #{r.id} {r.source === 'seed' ? '(seed)' : ''}
            </div>
            <div>
              Heuristic estimate <span className="tnum">{r.haze_score.toFixed(0)}</span> / 500
            </div>
            <div>
              Trust weight <span className="tnum">{r.trust_weight.toFixed(2)}</span>
            </div>
          </Tooltip>
        </CircleMarker>
      ))}
    </MapContainer>
  )
}
