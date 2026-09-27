import { CircleMarker, MapContainer, TileLayer, Tooltip } from 'react-leaflet'
import type { CitizenReport } from '../types'
import { CITIES, cityLabel, INDIA_BOUNDS, isCohort } from '../cities'

// Structural ink for vector edges so markers stay legible on light OSM tiles.
const SOOT = '#211e1a'
const PANEL = '#f2eee6'
const OCHRE = '#b0763a'

// AQI-proxy severity ramp. Concrete hexes (Leaflet pathOptions cannot read CSS
// vars) that mirror the --sev-* tokens in index.css: heat rises with severity,
// staying inside the warm dust/ochre/ember family instead of a green-to-purple
// rainbow.
export function hazeColor(score: number): string {
  if (score <= 200) return '#c6b184' // Moderate: pale dust
  if (score <= 300) return '#c08a3e' // Poor: ochre-amber
  if (score <= 400) return '#b0552a' // Very Poor: burnt orange
  return '#7e2d14' // Severe: charred rust
}

export function severityLabel(score: number): string {
  if (score <= 200) return 'Moderate'
  if (score <= 300) return 'Poor'
  if (score <= 400) return 'Very Poor'
  return 'Severe'
}

interface Props {
  reports: CitizenReport[]
}

export default function MapView({ reports }: Props) {
  return (
    <MapContainer bounds={INDIA_BOUNDS} boundsOptions={{ padding: [24, 24] }} scrollWheelZoom style={{ height: '100%', width: '100%' }}>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {/* City nodes are neutral infrastructure; only real citizen data carries AQI
          colour. The cohort that trains the shared model is filled ochre, the same
          colour the federation uses in the loss chart. */}
      {CITIES.map((c) => {
        const cohort = isCohort(c.key)
        return (
          <CircleMarker
            key={c.key}
            center={[c.lat, c.lon]}
            radius={cohort ? 8 : 5}
            pathOptions={{
              color: SOOT,
              weight: cohort ? 2 : 1.4,
              fillColor: cohort ? OCHRE : PANEL,
              fillOpacity: 1,
            }}
          >
            <Tooltip className="vayu-tooltip" direction="top">
              <span className="font-semibold">{c.label}</span> ·{' '}
              {cohort ? 'federated cohort node' : 'city node'}
            </Tooltip>
          </CircleMarker>
        )
      })}
      {reports.map((r) => (
        <CircleMarker
          key={r.id}
          center={[r.latitude, r.longitude]}
          radius={6}
          pathOptions={{ color: SOOT, weight: 1, fillColor: hazeColor(r.haze_score), fillOpacity: 1 }}
        >
          <Tooltip className="vayu-tooltip" direction="top">
            <div className="font-semibold">Citizen report #{r.id}</div>
            <div>
              Haze score <span className="tnum">{r.haze_score.toFixed(0)}</span> / 500 ({severityLabel(r.haze_score)})
            </div>
            <div>
              Confidence <span className="tnum">{(r.confidence * 100).toFixed(0)}%</span>
            </div>
            <div>{cityLabel(r.city)}</div>
          </Tooltip>
        </CircleMarker>
      ))}
    </MapContainer>
  )
}
