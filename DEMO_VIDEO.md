# VayuSetu — 4-minute demo video script (1080p, screen + voice)

Rehearse once with `DEMO.md` before recording. All data in the app is
generated — the "Synthetic demonstration data" label is part of the story,
not a caveat to hide.

| Time | Show | Say |
|---|---|---|
| **0:00** | **Map tab, all cities.** Let the map settle; hover one tier-1 marker and one tier-3 (dashed) marker. | "Air-quality monitors are sparse, and cities cannot share raw data. VayuSetu shares **models, not data**. Every marker is a city node — filled means ground monitoring, a ring means weather-and-satellite only, and the dashed ones are cities we still serve by inferring from their neighbours. Note the label in the header: everything here is **synthetic demonstration data**." |
| **0:30** | **Submit a manual report, then a photo report.** Click the map near Kanpur, pick "Hazy" in the dropdown, Submit. Then again near Delhi with a sky photo (any photo on disk). Point at the two new pins and the city readout. | "Anyone can contribute. A report is scored — this one is manual, this one from a photo — and **trust-weighted against the nearest monitor**: the closer your score is to the station's reading, the more it counts. Watch the citizen-adjusted AQI move as the reports blend in. And to be precise: the photo score is a **heuristic estimate** for now, not a measurement." |
| **1:15** | **Federated tab, start training.** Click *Start federated training*; while rounds tick up, hover the chart and name two of the faint lines. | "This is the core. Each faint line is **one city training locally** on its own daily records. The red global line appears each time the server **averages the weights** — the only thing that ever crosses a city's boundary. Twenty cities are in this round, and not one raw observation moved." |
| **2:00** | **Results table.** Scroll to "Did federation help?" and point row by row. | "Here are the results, **exactly as measured** — persistence, what a forecaster would do with yesterday's number; local-only, each city training alone; federated, the shared model; and **personalized**, the shared model after each city fine-tunes it privately on its own data. Nothing here is tuned to flatter the federation — if it loses on a city, the table says so." |
| **2:30** | **Hotspots tab, drag the wind vector.** In "Trace the wind", drag the handle from a fire hotspot toward its downwind city. | "Fires and industrial zones become hotspots. Combine them with the wind and the app computes the **downwind city and an ETA** — drag the handle to watch the plume age on its way: distance covered, hours to arrival, and how much strength it keeps." |
| **3:00** | **Forecast for a monitored city, then a tier-2 city.** In the city selector pick Delhi, then Varanasi. Point at the band, then the method label. | "Forecasts come in two flavours. For a monitored city like Delhi, this is the **federated model** — the shaded band is its measured uncertainty. For a city with no monitor, like Varanasi, the chart is **interpolated from nearby cities**, and the label says so honestly." |
| **3:30** | **Alerts tab, acknowledge.** Click Acknowledge on the Delhi alert. | "When a forecast crosses a threshold, the right response is attached: Delhi-NCR gets its **GRAP stage**; other cities get a state advisory. SMS here is **simulated** — nothing is really sent. Acknowledge clears it." |
| **3:50** | **Deck slide 11.** Cut to the slide, hold two seconds, close. | "Scaling this nationwide doesn't mean shipping data to a central server. **Adding a city means running a node.** VayuSetu — many cities, one model, zero raw data shared." |

## Recording checklist

- [ ] Record at **1080p**, screen + voice, browser zoom 100%, bookmarks bar hidden.
- [ ] Start from a fresh page load; close other tabs so the browser tab strip is clean.
- [ ] Before take 2 of the FL tab: the run must be **completed** from a previous rehearsal, or the table won't show — start the run ~90 s before recording that segment, or record that segment last.
- [ ] Have two photos ready on disk (one clear sky, one hazy) for the 0:30 segment.
- [ ] Keep the cursor still while narrating numbers; move it only when pointing.
- [ ] If the Render backend is cold (first load >60 s), warm it by opening the site once before recording.
