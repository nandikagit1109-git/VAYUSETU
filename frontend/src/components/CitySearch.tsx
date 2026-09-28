import { useMemo, useState } from 'react'
import type { City } from '../types'

interface Props {
  cities: City[]
  value: string | null
  onChange: (cityId: string) => void
  id?: string
}

// Search + select over the national registry: exact/prefix match shortcuts,
// grouped options by state for the full dropdown.
export default function CitySearch({ cities, value, onChange, id = 'city-search' }: Props) {
  const [query, setQuery] = useState('')

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return cities
    return cities.filter((c) => c.city_id.includes(q) || c.name.toLowerCase().includes(q) || c.state.toLowerCase().includes(q))
  }, [cities, query])

  const states = useMemo(() => {
    const order: string[] = []
    const byState = new Map<string, City[]>()
    for (const c of filtered) {
      if (!byState.has(c.state)) {
        byState.set(c.state, [])
        order.push(c.state)
      }
      byState.get(c.state)!.push(c)
    }
    return order.map((s) => [s, byState.get(s)!] as const)
  }, [filtered])

  return (
    <div>
      <label className="label" htmlFor={id}>
        City
      </label>
      <input
        id={`${id}-filter`}
        className="field mb-2"
        placeholder="Filter cities…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        autoComplete="off"
      />
      <select id={id} className="field" value={value ?? ''} onChange={(e) => onChange(e.target.value)}>
        <option value="" disabled>
          Choose a city…
        </option>
        {states.map(([state, list]) => (
          <optgroup key={state} label={state}>
            {list.map((c) => (
              <option key={c.city_id} value={c.city_id}>
                {c.name}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
    </div>
  )
}
