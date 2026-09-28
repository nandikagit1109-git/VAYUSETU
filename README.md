# VayuSetu — Federated Hyperlocal Air-Quality Intelligence

A national platform where **each Indian city is a federated node**. Cities hold
their own data; only model weights leave a city. The system builds a nationwide
daily master dataset, assigns every city a coverage tier from its data, trains
one shared forecasting model with federated averaging (FedAvg) across all
tier-1 cities, serves +1/+2/+3 day AQI forecasts everywhere (neighbour
interpolation where there is no ground truth), detects fire/industrial
hotspots with wind-based downwind transport, blends citizen reports into
per-city adjusted AQI, and fires alerts with GRAP/advisory actions —
**fully functional offline** on seeded synthetic demonstration data.

## Start everything (one command)

```bash
docker compose up --build
```

Then open **http://localhost:5173** (backend API: http://localhost:8000/health).

No API keys, no internet and no manual steps are required. With no
configuration the app runs in `DATA_MODE=synthetic`: 28 active cities
(20 tier-1, 5 tier-2, 3 tier-3), a deterministic 2-year daily dataset, and a
federated training run that starts automatically in the background on first
boot. The UI carries a persistent "Synthetic demonstration data" label, and
the photo scorer is labelled a heuristic estimate.

### The 4 tabs

1. **Map & Report** — India-wide map of all 28 active cities (marker size by
   latest AQI; tier shown by stroke style: filled = ground monitoring, ring =
   weather/satellite only, dashed ring = inferred from neighbours). Click the
   map to drop a report pin, attach a sky photo or a manual visibility level,
   and the server assigns the nearest city, scores the report, and pins it
   immediately; the city's citizen-adjusted AQI updates.
2. **Federated Learning** — press *Start federated training* to watch every
   participating tier-1 city's local loss line converge with the aggregated
   global line over 8 rounds. Below, a compact table reports validation MAE
   per city for the persistence baseline, local-only training, and the
   federated model — exactly as measured, with no tuning to flatter the
   federation. Excluded cities (too few training windows) are listed with
   reasons.
3. **Hotspots & Forecast** — fire detections from the last two days (top 12 by
   intensity) plus industrial zones, each with a wind vector (direction the
   wind blows **toward**), a plume path to the nearest city inside the wind
   cone, and a travel-time ETA. A city selector shows 30 days of observed
   history followed by the +1/+2/+3 day forecast with an uncertainty band and
   the method label ("federated model", "persistence baseline", or
   "interpolated from nearby cities").
4. **Alerts** — the checker runs on load and every 30 s; when a city's worst
   +1/+2/+3 day forecast crosses 200 an alert fires with the GRAP stage for
   Delhi-NCR cities or a generic advisory elsewhere. Alerts can be
   acknowledged; SMS channels are simulated and labelled as such.

## Switching to real data

Real-data mode is opt-in and never crashes the app: on any missing file or
schema mismatch the backend logs a warning, falls back to synthetic data, and
reports the reason in `/api/meta` as `fallback_reason`.

1. Place files under `backend/data/raw/` (see `backend/data/raw/README.md`):
   - `cpcb/city_day.csv` — CPCB city-level daily pollution. Cities are
     **discovered from the file**, never assumed; registry cities not present
     are skipped with a warning.
   - `power/{city_id}.csv` — NASA POWER daily weather (`-999` sentinels become
     missing values).
   - `firms/*.csv` — NASA FIRMS fire points (optional; absent means the UI
     says "fire data not loaded").
   - `s5p/{city_id}.csv` — optional Sentinel-5P columns.
2. Set `DATA_MODE=real` in `.env` (copy `.env.example`) and restart.
3. The optional fetch scripts in `backend/scripts/` are **manual and need
   internet**; they are never run at app start:
   - `python scripts/fetch_nasa_power.py` — keyless NASA POWER daily point API.
   - `FIRMS_MAP_KEY=... python scripts/fetch_firms.py` — exits with a clear
     message if the key is missing.
   - `python scripts/fetch_s5p_gee.py` — stretch, needs Earth Engine auth.

## Local development without Docker

Backend (Python 3.11):

```bash
cd backend
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt   # Windows
# torch installs CPU wheels in Docker; locally: pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv/Scripts/python -m uvicorn app.main:app --port 8000
```

Frontend (Node 18+):

```bash
cd frontend
npm install
npm run dev        # serves http://localhost:5173, proxies /api to :8000
```

## Tests and self-verification

```bash
docker compose run backend pytest          # unit + API contract tests
docker compose run backend python scripts/verify_demo.py
```

`verify_demo.py` starts from a clean `data/processed`, runs the app
in-process, waits for the first federated run (timeout 180 s), and prints a
PASS/FAIL line for every programmatically checkable definition-of-done item;
it exits non-zero on any FAIL.

## How it works (short version)

- **Data** (`backend/app/data/`): a 35-city registry (`cities.csv` with
  synthetic roles `ground` / `aux_only` / `none` / `skip`), a deterministic
  seed-42 synthetic generator (seasonality, AR(1) noise, Punjab/Haryana
  stubble transport with distance-band lags, fire points, weather, satellite
  columns with cloud gaps), real-data loaders with schema validation, the
  master daily table (`data/processed/master_daily.csv`), and data-driven
  tiering (tier 1 = ≥90 ground days, tier 2 = ≥30 weather days, tier 3 =
  nothing).
- **Federated learning** (`backend/app/federated/`): a 23-feature → GRU(32) →
  3-horizon model with fixed global scaling; `FLClient` holds only its own
  city's windows; the server computes the sample-weighted FedAvg and never
  imports the data layer; the runner writes `fl_status.json` atomically after
  each round and `fl_eval.json` with honest baselines; `global_model.pt`
  persists the result and is reused across restarts.
- **Serving** (`backend/app/services/`): forecasts per tier with bounds from
  validation residual p90 (or the h-day change std for persistence), wind
  geometry (wind_dir is where wind comes FROM), CPCB AQI breakpoints, the
  idempotent alert checker, GRAP stage rules, and the heuristic photo scorer.

## Runtime notes

- All randomness is seeded (42) at startup and at the start of every FL run;
  the same inputs produce the same charts on every run.
- `GET /health` returns `{"ok": true}` for the docker healthcheck.
- Every JSON response passes a sanitiser (numpy → Python, NaN/Inf → null) and
  every failure uses the envelope `{"error": true, "message": ...}`.
- Dates are plain `YYYY-MM-DD`; timestamps are UTC-aware ISO-8601.
