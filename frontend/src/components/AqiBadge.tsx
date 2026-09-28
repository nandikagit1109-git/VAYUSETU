// AQI severity helpers shared by map, lists and charts. Colours mirror the
// --sev-* tokens (Leaflet pathOptions cannot read CSS vars, so hex literals).
export function aqiColor(aqi: number): string {
  if (aqi <= 100) return '#c6b184' // Good/Satisfactory: pale dust
  if (aqi <= 200) return '#c6b184' // Moderate: pale dust
  if (aqi <= 300) return '#c08a3e' // Poor: ochre-amber
  if (aqi <= 400) return '#b0552a' // Very Poor: burnt orange
  return '#7e2d14' // Severe: charred rust
}

export function aqiCategory(aqi: number): string {
  if (aqi <= 50) return 'Good'
  if (aqi <= 100) return 'Satisfactory'
  if (aqi <= 200) return 'Moderate'
  if (aqi <= 300) return 'Poor'
  if (aqi <= 400) return 'Very Poor'
  return 'Severe'
}

export function fmtAqi(aqi: number | null | undefined): string {
  return aqi == null ? '—' : aqi.toFixed(0)
}
