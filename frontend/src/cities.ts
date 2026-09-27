// City network for VayuSetu. Mirrors backend/app/cities.py exactly: the keys are
// what the API stores and filters on, the labels are what the UI shows. If a city
// is added or renamed, both files must change together.

export interface City {
  key: string
  label: string
  lat: number
  lon: number
}

// Delhi, Kanpur and Pune head the list because they are the federated cohort and
// their seeded AQI history must stay byte-identical across regenerations.
export const CITIES: City[] = [
  { key: 'delhi', label: 'Delhi', lat: 28.6139, lon: 77.209 },
  { key: 'kanpur', label: 'Kanpur', lat: 26.4499, lon: 80.3319 },
  { key: 'pune', label: 'Pune', lat: 18.5204, lon: 73.8567 },
  { key: 'mumbai', label: 'Mumbai', lat: 19.076, lon: 72.8777 },
  { key: 'bengaluru', label: 'Bengaluru', lat: 12.9716, lon: 77.5946 },
  { key: 'hyderabad', label: 'Hyderabad', lat: 17.385, lon: 78.4867 },
  { key: 'ahmedabad', label: 'Ahmedabad', lat: 23.0225, lon: 72.5714 },
  { key: 'chennai', label: 'Chennai', lat: 13.0827, lon: 80.2707 },
  { key: 'kolkata', label: 'Kolkata', lat: 22.5726, lon: 88.3639 },
  { key: 'surat', label: 'Surat', lat: 21.1702, lon: 72.8311 },
  { key: 'jaipur', label: 'Jaipur', lat: 26.9124, lon: 75.7873 },
  { key: 'lucknow', label: 'Lucknow', lat: 26.8467, lon: 80.9462 },
  { key: 'nagpur', label: 'Nagpur', lat: 21.1458, lon: 79.0882 },
  { key: 'indore', label: 'Indore', lat: 22.7196, lon: 75.8573 },
  { key: 'bhopal', label: 'Bhopal', lat: 23.2599, lon: 77.4126 },
  { key: 'patna', label: 'Patna', lat: 25.5941, lon: 85.1376 },
  { key: 'ludhiana', label: 'Ludhiana', lat: 30.9009, lon: 75.8573 },
  { key: 'chandigarh', label: 'Chandigarh', lat: 30.7333, lon: 76.7794 },
  { key: 'agra', label: 'Agra', lat: 27.1767, lon: 78.0081 },
  { key: 'varanasi', label: 'Varanasi', lat: 25.3176, lon: 82.9739 },
  { key: 'nashik', label: 'Nashik', lat: 19.9975, lon: 73.7898 },
  { key: 'vadodara', label: 'Vadodara', lat: 22.3072, lon: 73.1812 },
  { key: 'jodhpur', label: 'Jodhpur', lat: 26.2389, lon: 73.0243 },
  { key: 'ranchi', label: 'Ranchi', lat: 23.3441, lon: 85.3096 },
  { key: 'bhubaneswar', label: 'Bhubaneswar', lat: 20.2961, lon: 85.8245 },
  { key: 'raipur', label: 'Raipur', lat: 21.2514, lon: 81.6296 },
  { key: 'guwahati', label: 'Guwahati', lat: 26.1445, lon: 91.7362 },
  { key: 'coimbatore', label: 'Coimbatore', lat: 11.0168, lon: 76.9558 },
  { key: 'thiruvananthapuram', label: 'Thiruvananthapuram', lat: 8.5241, lon: 76.9366 },
  { key: 'vijayawada', label: 'Vijayawada', lat: 16.5062, lon: 80.648 },
  { key: 'dehradun', label: 'Dehradun', lat: 30.3165, lon: 78.0322 },
  { key: 'srinagar', label: 'Srinagar', lat: 34.0837, lon: 74.7973 },
  { key: 'shimla', label: 'Shimla', lat: 31.1048, lon: 77.1734 },
  { key: 'panaji', label: 'Panaji', lat: 15.4909, lon: 73.8278 },
  { key: 'puducherry', label: 'Puducherry', lat: 11.9416, lon: 79.8083 },
  { key: 'imphal', label: 'Imphal', lat: 24.817, lon: 93.9368 },
  { key: 'shillong', label: 'Shillong', lat: 25.5788, lon: 91.8933 },
  { key: 'agartala', label: 'Agartala', lat: 23.8315, lon: 91.2868 },
  { key: 'aizawl', label: 'Aizawl', lat: 23.7271, lon: 92.7176 },
  { key: 'kohima', label: 'Kohima', lat: 25.6751, lon: 94.1083 },
  { key: 'itanagar', label: 'Itanagar', lat: 27.084, lon: 93.605 },
  { key: 'gangtok', label: 'Gangtok', lat: 27.3389, lon: 88.6065 },
  { key: 'leh', label: 'Leh', lat: 34.1526, lon: 77.5771 },
  { key: 'port_blair', label: 'Port Blair', lat: 11.6234, lon: 92.7265 },
]

export const CITY_COORDS: Record<string, [number, number]> = Object.fromEntries(
  CITIES.map((c) => [c.key, [c.lat, c.lon]]),
)

export const CITY_LABELS: Record<string, string> = Object.fromEntries(CITIES.map((c) => [c.key, c.label]))

// The three cities that train the shared model. Every other city still reports,
// forecasts and alerts; it just is not in this round's cohort.
export const FEDERATED_COHORT = ['delhi', 'kanpur', 'pune'] as const

export const isCohort = (key: string): boolean => (FEDERATED_COHORT as readonly string[]).includes(key)

export function cityLabel(key: string): string {
  return CITY_LABELS[key] ?? key
}

// Map bounds fitted to the network rather than hardcoded to one region, so every
// city node is on screen at load. Used by both Leaflet maps.
const lats = CITIES.map((c) => c.lat)
const lons = CITIES.map((c) => c.lon)
export const INDIA_BOUNDS: [[number, number], [number, number]] = [
  [Math.min(...lats), Math.min(...lons)],
  [Math.max(...lats), Math.max(...lons)],
]
