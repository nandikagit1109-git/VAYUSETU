import { useEffect, useState } from 'react'
import { getReports } from './api'
import type { CitizenReport } from './types'
import AlertsPanel from './components/AlertsPanel'
import FederatedPanel from './components/FederatedPanel'
import ForecastChart from './components/ForecastChart'
import HotspotOverlay from './components/HotspotOverlay'
import MapView from './components/MapView'
import ReportForm from './components/ReportForm'

type Tab = 'map' | 'federated' | 'hotspots' | 'alerts'

const TABS: { id: Tab; label: string }[] = [
  { id: 'map', label: 'Map & Report' },
  { id: 'federated', label: 'Federated Learning' },
  { id: 'hotspots', label: 'Hotspots & Forecast' },
  { id: 'alerts', label: 'Alerts' },
]

function MapReportTab() {
  const [reports, setReports] = useState<CitizenReport[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    getReports()
      .then((d) => {
        if (active) setReports(d.reports ?? [])
      })
      .catch((err) => {
        if (active) setLoadError(err instanceof Error ? err.message : 'Could not load existing reports.')
      })
    return () => {
      active = false
    }
  }, [])

  return (
    <div className="grid gap-4 lg:grid-cols-[380px_1fr]">
      <div>
        <ReportForm onCreated={(pin) => setReports((prev) => [pin, ...prev])} />
        {loadError && (
          <div className="mt-3 rounded-lg border border-amber-800 bg-amber-950/50 px-3 py-2 text-xs text-amber-300">
            {loadError} (new submissions still work)
          </div>
        )}
      </div>
      <div className="h-[600px] overflow-hidden rounded-xl border border-slate-800">
        <MapView reports={reports} />
      </div>
    </div>
  )
}

export default function App() {
  const [tab, setTab] = useState<Tab>('map')

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-4 px-6 py-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-50">
              Vayu<span className="text-sky-400">Setu</span>
            </h1>
            <p className="text-xs text-slate-400">Federated hyperlocal air-quality intelligence</p>
          </div>
          <nav className="ml-auto flex flex-wrap gap-1">
            {TABS.map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                  tab === t.id ? 'bg-sky-600 text-white' : 'text-slate-300 hover:bg-slate-800'
                }`}
              >
                {t.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-6">
        {tab === 'map' && <MapReportTab />}
        {tab === 'federated' && <FederatedPanel />}
        {tab === 'hotspots' && (
          <div className="grid gap-4">
            <HotspotOverlay />
            <ForecastChart />
          </div>
        )}
        {tab === 'alerts' && <AlertsPanel />}
      </main>

      <footer className="mx-auto max-w-7xl px-6 pb-6 text-center text-[11px] text-slate-600">
        Demo MVP — all satellite, sensor and SMS data sources are simulated offline with fixed seeds.
      </footer>
    </div>
  )
}
