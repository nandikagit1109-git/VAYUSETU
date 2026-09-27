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

// Custom brand mark: a sun disc cut by two horizontal haze bands, drawn for this
// product (smog occluding the sky). No stock icon library.
function BrandMark() {
  return (
    <svg viewBox="0 0 28 28" width="30" height="30" aria-hidden="true" className="shrink-0">
      <circle cx="14" cy="14" r="8.5" fill="var(--ochre)" />
      <rect x="1.5" y="11.8" width="25" height="2.8" fill="var(--panel)" />
      <rect x="3.5" y="16.8" width="21" height="2.8" fill="var(--panel)" />
    </svg>
  )
}

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
    // The map dominates its tab; the report form is a narrow side rail, not a card in a grid.
    <div className="grid gap-4 lg:grid-cols-[340px_1fr]">
      <div className="flex flex-col gap-3">
        <ReportForm onCreated={(pin) => setReports((prev) => [pin, ...prev])} />
        {loadError && (
          <div className="banner-warn">
            {loadError} New submissions still work.
          </div>
        )}
      </div>
      <div className="panel h-[70vh] min-h-[480px] overflow-hidden">
        <MapView reports={reports} />
      </div>
    </div>
  )
}

export default function App() {
  const [tab, setTab] = useState<Tab>('map')

  return (
    <div className="flex min-h-screen flex-col bg-haze">
      <header className="sticky top-0 z-[1100] border-b border-hairline bg-panel">
        <div className="mx-auto flex w-full max-w-[1400px] flex-wrap items-center gap-x-6 gap-y-2 px-5 py-3">
          <div className="flex items-center gap-3">
            <BrandMark />
            <div>
              <h1 className="font-display text-[19px] font-extrabold leading-none text-soot">
                Vayu<span className="text-ochre">Setu</span>
              </h1>
              <p className="mt-1 text-[11px] leading-none text-ash">Federated hyperlocal air-quality intelligence</p>
            </div>
          </div>

          <nav className="ml-auto flex flex-wrap items-center" aria-label="Sections">
            {TABS.map((t) => {
              const active = tab === t.id
              return (
                <button
                  key={t.id}
                  onClick={() => setTab(t.id)}
                  aria-current={active ? 'page' : undefined}
                  className={`relative px-3 py-2 text-sm font-medium transition-colors ${
                    active ? 'text-soot' : 'text-ash hover:text-soot'
                  }`}
                >
                  {t.label}
                  {/* Active-tab rule sits flush on the header's bottom hairline. */}
                  <span
                    className={`absolute inset-x-3 -bottom-3 h-[2px] ${active ? 'bg-ochre' : 'bg-transparent'}`}
                    aria-hidden="true"
                  />
                </button>
              )
            })}
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-[1400px] flex-1 px-5 py-5">
        {tab === 'map' && <MapReportTab />}
        {tab === 'federated' && <FederatedPanel />}
        {tab === 'hotspots' && (
          <div className="flex flex-col gap-4">
            <HotspotOverlay />
            <ForecastChart />
          </div>
        )}
        {tab === 'alerts' && <AlertsPanel />}
      </main>
    </div>
  )
}
