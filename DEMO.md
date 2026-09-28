# VayuSetu — 3-minute demo runbook

The live, always-ready copy of the app: **https://frontend-red-sigma-62.vercel.app**
(backend: https://vayusetu-backend.onrender.com). For the recorded video script,
see `DEMO_VIDEO.md`.

## Start

Local Docker:

```bash
docker compose up --build
```

Then open http://localhost:5173 (backend on http://localhost:8000/health).
Everything works offline in synthetic mode; no keys, no manual steps.

If the Render backend has been idle ~15 min it cold-starts: open the site once,
wait ~1–2 minutes (the first `/api/meta` response may lag), and it is warm.

## 3-minute click path

1. **Map & Report (0:00–0:45)** — the whole network on one map. Hover markers to
   show tier styles; point at the "Synthetic demonstration data" label.
   *Proves:* a national federated network with honest data labelling.
2. **Submit a report (0:45–1:15)** — click the map near a city, choose a
   visibility level, Submit. The pin appears instantly; the selected city's
   citizen-adjusted AQI changes. Optionally submit a photo report
   (`scorer: heuristic_v1`).
   *Proves:* citizen reports are scored, trust-weighted, and actually move the
   per-city estimate.
3. **Federated Learning (1:15–2:15)** — press *Start federated training*. One
   faint line per participating city; the ember global line appears as weights
   are averaged. After 8 rounds (~90 s), the results table shows persistence,
   local-only, federated, and personalized MAE — as measured. *(Rehearsal tip:
   start the run before the demo so the table is ready; the chart and table
   persist until a new run.)*
   *Proves:* federated averaging works live and is reported honestly.
4. **Hotspots & Forecast (2:15–2:40)** — hotspot map with wind vectors and
   plume paths; in "Trace the wind", drag the handle to show ETA. Then the
   forecast chart: Delhi (federated model) vs Varanasi (interpolated from
   nearby cities), band = uncertainty.
   *Proves:* source-to-impact transport and per-tier forecasting.
5. **Alerts (2:40–3:00)** — Delhi-NCR alert shows GRAP with a stage; other
   cities show ADVISORY; SMS chips say simulated. Click Acknowledge.
   *Proves:* forecast-driven, deduplicated, actionable alerts.

## Fallback plan (live-demo insurance)

- App misbehaves: **restart the backend** — locally `docker compose restart
  backend`, on Render the dashboard's Manual Deploy → "Clear build cache &
  deploy". Startup rebuilds everything deterministic in <15 s (training runs in
  the background; forecasts serve persistence meanwhile).
- Data looks corrupted: set `REBUILD_DATA=true` (compose env or Render env var)
  and restart — the master table regenerates from the seed, identical to before.
- No internet on the demo machine: everything is synthetic and offline-safe;
  only map tiles need the network, and the app degrades to a warm plain
  background without them. The frontend on Vercel needs no local machine at
  all — presenting from the browser is the safest option.
- Worst case, the recorded video in `DEMO_VIDEO.md` is the backup demo.
