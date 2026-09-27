import { CircleMarker, MapContainer, TileLayer, Tooltip } from 'react-leaflet'
import type { CitizenReport } from '../types'

export const CITY_COORDS: Record<string, [number, number]> = {
  delhi: [28.6139, 77.209],
  kanpur: [26.4499, 80.3319],
  pune: [18.5204, 73.8567],
}

export const CITY_LABELS: Record<string, string> = {
  delhi: 'Delhi',
  kanpur: 'Kanpur',
  pune: 'Pune',
}

export function hazeColor(score: number): string {
  if (score <= 200) return '#22c55e'
  if (score <= 300) return '#f59e0b'
  if (score <= 400) return '#ef4444'
  return '#a855f7'
}

interface Props {
  reports: CitizenReport[]
}

export default function MapView({ reports }: Props) {
  return (
    <MapContainer center={[23.5, 78.5]} zoom={5} scrollWheelZoom style={{ height: '100%', width: '100%' }}>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {Object.entries(CITY_COORDS).map(([city, pos]) => (
        <CircleMarker
          key={city}
          center={pos}
          radius={8}
          pathOptions={{ color: '#e2e8f0', fillColor: '#0ea5e9', fillOpacity: 0.9, weight: 2 }}
        >
          <Tooltip className="vayu-tooltip" direction="top">
            {CITY_LABELS[city] ?? city} (city node)
          </Tooltip>
        </CircleMarker>
      ))}
      {reports.map((r) => (
        <CircleMarker
          key={r.id}
          center={[r.latitude, r.longitude]}
          radius={6}
          pathOptions={{ color: '#0f172a', fillColor: hazeColor(r.haze_score), fillOpacity: 0.9, weight: 1 }}
        >
          <Tooltip className="vayu-tooltip" direction="top">
            <div>
              <div className="font-semibold">Citizen report #{r.id}</div>
              <div>Haze score: {r.haze_score.toFixed(0)} / 500</div>
              <div>Confidence: {(r.confidence * 100).toFixed(0)}%</div>
              <div>City: {r.city}</div>
            </div>
          </Tooltip>
        </CircleMarker>
      ))}
    </MapContainer>
  )
}
