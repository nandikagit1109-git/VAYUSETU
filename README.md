# VayuSetu — Federated Hyperlocal Air-Quality Intelligence

Hackathon demo MVP. A citizen-report map, a live federated-learning demo across
three city nodes (Delhi, Kanpur, Pune), emission hotspots with wind transport,
72-hour AQI forecasts, and GRAP-threshold alerts — **fully functional offline**:
all satellite/SMS/sensor data sources are simulated from bundled, seeded mock
datasets, and no API keys are required anywhere.

## Start everything (one command)

```bash
docker compose up --build
```

Then open **http://localhost:5173** (backend API: http://localhost:8000/api/health).

### The 4 tabs

1. **Map & Report** — Leaflet map with Delhi/Kanpur/Pune city nodes; submit a citizen report (sky photo or manual visibility) to get an instant simulated haze/AQI-proxy score that appears as a severity-colored pin without a page reload.
2. **Federated Learning** — press *Start Federated Training* to watch 3 city clients train a shared next-hour-AQI model with Flower FedAvg; the loss chart updates live round-by-round (8 rounds). Raw city data is never pooled — only model weight updates are aggregated.
3. **Hotspots & Forecast** — simulated satellite fire/industrial hotspots with wind-direction arrows and dashed plume paths (with ETA) to the downwind city, plus a 72-hour AQI forecast chart per city with an 80% confidence band.
4. **Alerts** — when a forecast crosses a GRAP threshold within 24h, an alert fires here with the matching GRAP stage action; acknowledge alerts in place. Thresholds are re-checked on load and every 30s.

## Runtime notes

- The federated simulation uses Flower's simulation API (Ray under the hood).
  The 8 training rounds themselves take ~22s; on a Windows laptop, Ray process
  startup adds ~30–40s of one-time overhead before the first round appears
  (~10–15s on Linux/Docker). The UI shows live progress throughout, and the
  status endpoint reports `running` until completion.
- Map tiles come from OpenStreetMap (no API key). With wifi off the map
  background is plain, but all markers, arrows and pins still render.
- All randomness is seeded (`np.random.seed(42)`, `torch.manual_seed(42)`), so
  every run produces identical charts and scores.

## Local development without Docker

Backend (Python 3.11):

```bash
cd backend
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt   # Windows
python seed_data_generator.py  # from repo root, regenerates backend/data/*
.venv/Scripts/python -m uvicorn app.main:app --port 8000
```

Frontend (Node 18+):

```bash
cd frontend
npm install
npm run dev        # serves http://localhost:5173, proxies /api to :8000
```

## Optional stretch integrations (off by default)

Copy `.env.example` to `.env` only if you want to enable them; the demo never
requires them and silently falls back to simulation:

- `ENABLE_TWILIO=true` + credentials — real SMS alerts (otherwise simulated).
- `ENABLE_LIVE_SATELLITE=true` — live fire data (otherwise bundled mock JSON).

## Regenerating deterministic seed data

```bash
python seed_data_generator.py
```

Rewrites `backend/data/historical_aqi_{delhi,kanpur,pune}.csv` (90 days hourly),
`fire_hotspots_mock.json`, and `wind_data_mock.json` — identical output on every
run thanks to the fixed seed.
