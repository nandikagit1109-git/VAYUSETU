import { useEffect, useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { getReports } from './api'
import type { CitizenReport, ReportResult } from './types'
import { DRIFT, DUR, EASE } from './motion'
import { useCities, useMeta } from './hooks'
import AlertsPanel from './components/AlertsPanel'
import CityInfoCard from './components/CityInfoCard'
import CitySearch from './components/CitySearch'
import FederatedPanel from './components/FederatedPanel'
import ForecastChart from './components/ForecastChart'
import HotspotOverlay from './components/HotspotOverlay'
import InfoAccordion from './components/InfoAccordion'
import MapView from './components/MapView'
import OnboardingIntro, { hasSeenIntro } from './components/OnboardingIntro'
import PointAqiCard from './components/PointAqiCard'
import ReportForm from './components/ReportForm'
import SevereBanner from './components/SevereBanner'
import SpotlightTour from './components/SpotlightTour'
import SyntheticLabel from './components/SyntheticLabel'

type Tab = 'map' | 'federated' | 'hotspots' | 'alerts'

const TABS: { id: Tab; label: string }[] = [
  { id: 'map', label: 'Map & Report' },
  { id: 'federated', label: 'Federated Learning' },
  { id: 'hotspots', label: 'Hotspots & Forecast' },
  { id: 'alerts', label: 'Alerts' },
]

const TAB_BLURB: Record<Tab, string> = {
  map: 'Citizen observations across the network',
  federated: 'Local training, aggregated weights',
  hotspots: 'Sources, transport and forecasts',
  alerts: 'Threshold crossings and recommended actions',
}

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

function TabGlyph({ tab }: { tab: Tab }) {
  const common = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.6, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const }
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" className="shrink-0 text-ochre">
      {tab === 'map' && (
        <>
          <path {...common} d="M12 21c-3.6-3.6-6-6.8-6-10a6 6 0 1 1 12 0c0 3.2-2.4 6.4-6 10z" />
          <circle {...common} cx="12" cy="10.5" r="2" />
        </>
      )}
      {tab === 'federated' && (
        <>
          <circle {...common} cx="5" cy="6" r="2" />
          <circle {...common} cx="5" cy="18" r="2" />
          <circle {...common} cx="19" cy="12" r="2.4" />
          <path {...common} d="M7 7l9 4M7 17l9-4" />
        </>
      )}
      {tab === 'hotspots' && (
        <>
          <path {...common} d="M4 12h11" />
          <path {...common} d="M12 8l4 4-4 4" />
          <circle {...common} cx="20" cy="12" r="1.4" />
        </>
      )}
      {tab === 'alerts' && (
        <>
          <path {...common} d="M12 4v3" />
          <path {...common} d="M6.5 8.5a7 7 0 0 1 11 0" />
          <path {...common} d="M4 12a10 10 0 0 1 16 0" />
          <circle {...common} cx="12" cy="18" r="1.6" />
        </>
      )}
    </svg>
  )
}

function MapReportTab() {
  const { cities, error: cityError } = useCities()
  const [reports, setReports] = useState<CitizenReport[]>([])
  const [reportError, setReportError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<string>('delhi')
  const [pin, setPin] = useState<{ lat: number; lon: number }>({ lat: 28.6139, lon: 77.209 })
  const [lastResult, setLastResult] = useState<ReportResult | null>(null)

  useEffect(() => {
    let active = true
    getReports()
      .then((d) => {
        if (active) setReports(d.reports ?? [])
      })
      .catch((err) => {
        if (active) setReportError(err instanceof Error ? err.message : 'Could not load existing reports.')
      })
    return () => {
      active = false
    }
  }, [])

  const selectedCity = cities.find((c) => c.city_id === selectedId) ?? null

  function handleCreated(report: CitizenReport, result: ReportResult) {
    setReports((prev) => [report, ...prev])
    setLastResult(result)
    setSelectedId(result.city_id)
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[340px_1fr]">
      <div className="flex flex-col gap-3">
        <ReportForm pinnedLatLon={pin} onCreated={handleCreated} />
        <div className="panel p-5">
          <CitySearch cities={cities} value={selectedId} onChange={setSelectedId} id="map-city-search" />
          <button
            type="button"
            className="btn-quiet mt-3 w-full"
            onClick={() => {
              if (selectedCity) setPin({ lat: selectedCity.latitude, lon: selectedCity.longitude })
            }}
          >
            Use {selectedCity?.name ?? 'city'} centre as report location
          </button>
        </div>
        <CityInfoCard city={selectedCity} />
        <PointAqiCard pin={pin} />
        {(reportError || cityError) && <div className="banner-warn">{reportError ?? cityError}</div>}
        {lastResult && lastResult.scorer === 'heuristic_v1' && (
          <div className="note">Photo score is a heuristic estimate, not a measurement.</div>
        )}
      </div>
      <div className="panel h-[70vh] min-h-[480px] overflow-hidden" data-tour="map">
        <MapView
          cities={cities}
          reports={reports}
          selectedCityId={selectedId}
          onSelectCity={setSelectedId}
          onMapPick={(lat, lon) => setPin({ lat, lon })}
        />
      </div>
    </div>
  )
}

function HotspotsTab() {
  const { cities } = useCities()
  const [cityId, setCityId] = useState<string>('delhi')
  return (
    <div className="flex flex-col gap-4">
      <ForecastChart cities={cities} selectedCityId={cityId} onSelectCity={setCityId} />
      <HotspotOverlay onPickCity={setCityId} />
    </div>
  )
}

export default function App() {
  const reduced = useReducedMotion()
  const meta = useMeta()
  const [tab, setTab] = useState<Tab>('map')
  const [introOpen, setIntroOpen] = useState(false)
  const [tourOpen, setTourOpen] = useState(false)

  // The three-beat intro runs once per browser, then stays out of the way.
  useEffect(() => {
    if (!hasSeenIntro()) setIntroOpen(true)
  }, [])

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

          <nav className="ml-auto flex flex-wrap items-center" aria-label="Sections" data-tour="tabs">
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
                  <span className={`absolute inset-x-3 -bottom-3 h-[2px] ${active ? 'bg-ochre' : 'bg-transparent'}`} aria-hidden="true" />
                </button>
              )
            })}
          </nav>

          <button type="button" className="btn-quiet shrink-0" onClick={() => setTourOpen(true)}>
            Show me around
          </button>
        </div>
      </header>

      <main className="mx-auto w-full max-w-[1400px] flex-1 px-5 py-5">
        <AnimatePresence mode="wait">
          <motion.div
            key={tab}
            initial={reduced ? { opacity: 0 } : { opacity: 0, y: DRIFT }}
            animate={{ opacity: 1, y: 0 }}
            exit={reduced ? { opacity: 0 } : { opacity: 0, y: DRIFT }}
            transition={reduced ? { duration: 0 } : { duration: DUR, ease: EASE }}
          >
            <div className="mb-4 flex flex-wrap items-center gap-3 text-ash">
              <TabGlyph tab={tab} />
              <span className="text-[11px] uppercase tracking-[0.08em]">{TAB_BLURB[tab]}</span>
              <span className="ml-auto">
                <SyntheticLabel />
              </span>
            </div>

            {tab === 'map' && <MapReportTab />}
            {tab === 'federated' && <FederatedPanel />}
            {tab === 'hotspots' && <HotspotsTab />}
            {tab === 'alerts' && <AlertsPanel />}
          </motion.div>
        </AnimatePresence>
      </main>

      {/* meta is fetched once at the shell level so the honesty label is always
          present; hooks below consume it via their own fetches. */}
      <span className="hidden" data-demo-now={meta?.demo_now ?? ''} />

      {/* "About this data" (section 13): real provenance, demo date and one
          sentence on what federated means here. Reachable from every tab. */}
      <footer className="mx-auto w-full max-w-[1400px] px-5 pb-6">
        <InfoAccordion title="About this data">
          <ul className="list-disc space-y-1 pl-4">
            {(meta?.sources ?? ['Loading data provenance…']).map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
          <p className="mt-2">
            Demonstration clock: {meta?.demo_now ?? '—'}. Federated here means each city
            trains on its own records and shares only model weights — raw measurements
            never leave a city node.
          </p>
        </InfoAccordion>
      </footer>

      <SevereBanner suppressed={tab === 'alerts' || introOpen || tourOpen} onView={() => setTab('alerts')} />

      <AnimatePresence>{introOpen && <OnboardingIntro key="intro" onDone={() => setIntroOpen(false)} />}</AnimatePresence>

      {tourOpen && <SpotlightTour onNavigate={(t) => setTab(t as Tab)} onClose={() => setTourOpen(false)} />}
    </div>
  )
}
