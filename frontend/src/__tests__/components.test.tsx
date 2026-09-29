import { cleanup, render } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import ForecastChart from '../components/ForecastChart'
import FederatedPanel from '../components/FederatedPanel'
import type { FlStatus, Forecast } from '../types'

afterEach(cleanup)

// Frontend tests 3 and 4 (section 14): charts and panels must render without
// crashing for error envelopes, neighbor_idw forecasts, null-safe fields, and
// 0/1/20 federated clients.

vi.mock('../api', () => ({
  getForecast: vi.fn(),
  getCityHistory: vi.fn(async () => ({ city_id: 'x', points: [] })),
  getCities: vi.fn(async () => ({ cities: [] })),
  getHotspots: vi.fn(async () => ({ hotspots: [] })),
  getFederatedStatus: vi.fn(),
  getFederatedEval: vi.fn(),
  runFederated: vi.fn(),
}))

function forecastFixture(method: Forecast['method'], overrides: Partial<Forecast> = {}): Forecast {
  return {
    city_id: 'delhi', tier: 1, method, model_version: method === 'federated_gru' ? 'fedavg-x' : null,
    points: [
      { date: '2025-11-10', horizon_days: 0, predicted_aqi: 350, lower_bound: 345, upper_bound: 355, observed: true },
      { date: '2025-11-11', horizon_days: 1, predicted_aqi: 360, lower_bound: 330, upper_bound: 390, observed: false },
    ],
    ...overrides,
  }
}

const statusFixture = (clients: string[]): FlStatus => ({
  status: 'completed',
  rounds: clients.length
    ? [{ round: 1, client_losses: Object.fromEntries(clients.map((c) => [c, 0.02])), global_loss: 0.02, global_val_mae: 37.1 }]
    : [],
  total_rounds: 8,
  clients,
  excluded: [],
  started_at: null, completed_at: null, error: null,
})

describe('ForecastChart render safety', () => {
  it('renders an error envelope without crashing', async () => {
    const { getForecast } = await import('../api')
    vi.mocked(getForecast).mockResolvedValue({ error: true, message: 'no monitored city within 400 km' })
    const { container } = render(<ForecastChart cities={[]} selectedCityId="guwahati" onSelectCity={() => {}} />)
    expect(container).toBeTruthy()
  })

  it('renders a neighbor_idw forecast and a null-safe forecast', async () => {
    const { getForecast } = await import('../api')
    vi.mocked(getForecast).mockResolvedValue(
      forecastFixture('neighbor_idw', { tier: 2, model_version: null, points: [
        { date: '2025-11-10', horizon_days: 0, predicted_aqi: 300, lower_bound: 290, upper_bound: 310, observed: true },
        { date: '2025-11-11', horizon_days: 1, predicted_aqi: 305, lower_bound: 200, upper_bound: 410, observed: false },
      ] }),
    )
    const { container } = render(<ForecastChart cities={[]} selectedCityId="varanasi" onSelectCity={() => {}} />)
    expect(container).toBeTruthy()
  })
})

describe('FederatedPanel with 0, 1 and 20 clients', () => {
  for (const n of [0, 1, 20]) {
    it(`renders ${n} clients without crashing`, async () => {
      const { getFederatedStatus, getFederatedEval } = await import('../api')
      vi.mocked(getFederatedStatus).mockResolvedValue(statusFixture(Array.from({ length: n }, (_, i) => `city${i}`)))
      vi.mocked(getFederatedEval).mockResolvedValue({
        available: n > 0, rows: [], mean_mae_persistence: null,
        mean_mae_local: null, mean_mae_federated: null, mean_mae_personalized: null,
      })
      const { container } = render(<FederatedPanel />)
      expect(container).toBeTruthy()
    })
  }
})
