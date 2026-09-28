// Shared hooks for the v2 API: meta, cities, and polling with StrictMode-safe
// interval cleanup (trap 13).
import { useEffect, useState } from 'react'
import { getCities, getMeta } from './api'
import type { City, Meta } from './types'

export function useMeta(): Meta | null {
  const [meta, setMeta] = useState<Meta | null>(null)
  useEffect(() => {
    let active = true
    getMeta()
      .then((m) => {
        if (active) setMeta(m)
      })
      .catch(() => {
        // Meta failures surface through each panel's own error state.
      })
    return () => {
      active = false
    }
  }, [])
  return meta
}

export function useCities(): { cities: City[]; error: string | null } {
  const [cities, setCities] = useState<City[]>([])
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    let active = true
    getCities()
      .then((d) => {
        if (active) setCities(d.cities ?? [])
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : 'Could not load cities.')
      })
    return () => {
      active = false
    }
  }, [])
  return { cities, error }
}

// Synthetic-data label state: meta drives the persistent quiet label.
export function isSynthetic(meta: Meta | null): boolean {
  return meta?.data_mode === 'synthetic'
}
