"""Deterministic seed data generator for VayuSetu.

Produces (under backend/data/):
  - historical_aqi_{city}.csv for every city in the master table : 90 days of
    synthetic hourly AQI with diurnal + weekly seasonality and noise, drawn from
    one global np.random.seed(42) so re-running setup never changes the charts.
  - fire_hotspots_mock.json : fixed stubble-burning points near Punjab/Haryana,
    industrial points near Kanpur, plus sources across the rest of the network.
  - wind_data_mock.json : fixed per-region wind direction/speed so hotspots
    plausibly point at a downwind city with an ETA.

Run with:  python seed_data_generator.py   (cwd = repository root)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parent / "backend"
DATA_DIR = BACKEND_DIR / "data"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# The city table is shared with the running backend so the two cannot drift.
from app.cities import CITY_TABLE  # noqa: E402

START = pd.Timestamp("2026-06-01 00:00:00")
HOURS = 90 * 24


def generate_csvs() -> None:
    # One global seed, consumed city by city in table order: the first three
    # entries (delhi, kanpur, pune) therefore keep the exact series they had
    # before the network was widened.
    np.random.seed(42)
    hours = pd.date_range(START, periods=HOURS, freq="h")
    hod = hours.hour.to_numpy(dtype=float)
    dow = hours.dayofweek.to_numpy(dtype=float)

    for p in CITY_TABLE:
        # Morning peak (~08:00) and evening peak (~21:00) diurnal pattern
        diurnal = p["amp"] * (
            0.55 * np.cos(2 * np.pi * (hod - 8.0) / 24.0)
            + 0.45 * np.cos(2 * np.pi * (hod - 21.0) / 24.0)
        )
        weekly = p["weekly"] * np.cos(2 * np.pi * (dow - 1.0) / 7.0)
        noise = np.random.normal(0.0, p["noise"], size=HOURS)
        aqi = np.clip(p["base"] + diurnal + weekly + noise, 10.0, 500.0)
        df = pd.DataFrame(
            {
                "timestamp": hours.strftime("%Y-%m-%dT%H:%M:%S"),
                "aqi": np.round(aqi, 2),
            }
        )
        out = DATA_DIR / f"historical_aqi_{p['key']}.csv"
        df.to_csv(out, index=False)
        print(f"wrote {out} ({len(df)} rows)")


# Each source sits upwind of the city it is meant to reach, given the bearing the
# nearest wind region blows toward. Positions are demo fixtures, not observations.
FIRE_HOTSPOTS = {
    "hotspots": [
        # Stubble burning near Punjab/Haryana -> blown SE toward Delhi
        {"latitude": 30.70, "longitude": 75.90, "cause": "stubble_burning", "confidence": 0.91, "detected_at": "2026-09-20T06:00:00+00:00"},
        {"latitude": 30.30, "longitude": 76.20, "cause": "stubble_burning", "confidence": 0.87, "detected_at": "2026-09-20T07:30:00+00:00"},
        {"latitude": 29.90, "longitude": 75.50, "cause": "stubble_burning", "confidence": 0.83, "detected_at": "2026-09-20T08:15:00+00:00"},
        {"latitude": 30.50, "longitude": 76.50, "cause": "stubble_burning", "confidence": 0.79, "detected_at": "2026-09-21T05:45:00+00:00"},
        {"latitude": 30.10, "longitude": 75.20, "cause": "stubble_burning", "confidence": 0.74, "detected_at": "2026-09-21T06:30:00+00:00"},
        {"latitude": 29.70, "longitude": 76.00, "cause": "stubble_burning", "confidence": 0.68, "detected_at": "2026-09-21T09:00:00+00:00"},
        # Industrial belt west/south-west of Kanpur -> blown east toward Kanpur
        {"latitude": 26.50, "longitude": 80.05, "cause": "industrial", "confidence": 0.88, "detected_at": "2026-09-22T04:00:00+00:00"},
        {"latitude": 26.30, "longitude": 80.00, "cause": "industrial", "confidence": 0.81, "detected_at": "2026-09-22T05:30:00+00:00"},
        {"latitude": 26.35, "longitude": 79.95, "cause": "industrial", "confidence": 0.72, "detected_at": "2026-09-22T07:00:00+00:00"},
        # Rest of the network: each point upwind of the city it reaches
        {"latitude": 31.40, "longitude": 75.30, "cause": "stubble_burning", "confidence": 0.89, "detected_at": "2026-09-23T05:15:00+00:00"},
        {"latitude": 31.10, "longitude": 76.30, "cause": "stubble_burning", "confidence": 0.88, "detected_at": "2026-09-23T06:00:00+00:00"},
        {"latitude": 22.90, "longitude": 71.90, "cause": "industrial", "confidence": 0.86, "detected_at": "2026-09-23T07:30:00+00:00"},
        {"latitude": 27.60, "longitude": 77.40, "cause": "stubble_burning", "confidence": 0.85, "detected_at": "2026-09-23T08:45:00+00:00"},
        {"latitude": 18.75, "longitude": 72.30, "cause": "industrial", "confidence": 0.84, "detected_at": "2026-09-24T04:30:00+00:00"},
        {"latitude": 21.90, "longitude": 88.20, "cause": "industrial", "confidence": 0.83, "detected_at": "2026-09-24T05:45:00+00:00"},
        {"latitude": 23.20, "longitude": 76.60, "cause": "industrial", "confidence": 0.81, "detected_at": "2026-09-24T07:00:00+00:00"},
        {"latitude": 17.40, "longitude": 77.60, "cause": "industrial", "confidence": 0.82, "detected_at": "2026-09-24T08:15:00+00:00"},
        {"latitude": 21.20, "longitude": 72.10, "cause": "industrial", "confidence": 0.80, "detected_at": "2026-09-25T04:00:00+00:00"},
        {"latitude": 26.80, "longitude": 80.20, "cause": "industrial", "confidence": 0.80, "detected_at": "2026-09-25T05:15:00+00:00"},
        {"latitude": 21.10, "longitude": 78.20, "cause": "industrial", "confidence": 0.78, "detected_at": "2026-09-25T06:30:00+00:00"},
        {"latitude": 21.20, "longitude": 80.80, "cause": "industrial", "confidence": 0.77, "detected_at": "2026-09-25T07:45:00+00:00"},
        {"latitude": 12.60, "longitude": 77.00, "cause": "vehicular", "confidence": 0.77, "detected_at": "2026-09-25T09:00:00+00:00"},
        {"latitude": 27.50, "longitude": 75.20, "cause": "stubble_burning", "confidence": 0.76, "detected_at": "2026-09-26T04:45:00+00:00"},
        {"latitude": 23.30, "longitude": 84.40, "cause": "industrial", "confidence": 0.75, "detected_at": "2026-09-26T06:00:00+00:00"},
        {"latitude": 25.30, "longitude": 82.10, "cause": "stubble_burning", "confidence": 0.74, "detected_at": "2026-09-26T07:15:00+00:00"},
        {"latitude": 19.60, "longitude": 85.50, "cause": "industrial", "confidence": 0.73, "detected_at": "2026-09-26T08:30:00+00:00"},
        {"latitude": 26.10, "longitude": 91.00, "cause": "stubble_burning", "confidence": 0.71, "detected_at": "2026-09-27T04:15:00+00:00"},
        {"latitude": 34.40, "longitude": 74.30, "cause": "stubble_burning", "confidence": 0.68, "detected_at": "2026-09-27T05:30:00+00:00"},
        {"latitude": 25.60, "longitude": 84.30, "cause": "stubble_burning", "confidence": 0.79, "detected_at": "2026-09-27T06:45:00+00:00"},
        {"latitude": 18.30, "longitude": 73.20, "cause": "vehicular", "confidence": 0.65, "detected_at": "2026-09-27T08:00:00+00:00"},
        {"latitude": 13.10, "longitude": 80.90, "cause": "unknown", "confidence": 0.58, "detected_at": "2026-09-27T09:15:00+00:00"},
    ]
}

WIND_DATA = {
    "regions": [
        {
            "name": "punjab_haryana",
            "center_lat": 30.20,
            "center_lon": 75.90,
            "radius_km": 320.0,
            "direction_from_deg": 315.0,
            "speed_kmh": 14.0,
        },
        {
            "name": "kanpur_industrial",
            "center_lat": 26.45,
            "center_lon": 80.10,
            "radius_km": 160.0,
            "direction_from_deg": 270.0,
            "speed_kmh": 11.0,
        },
        {
            "name": "west_india",
            "center_lat": 19.00,
            "center_lon": 73.50,
            "radius_km": 300.0,
            "direction_from_deg": 250.0,
            "speed_kmh": 9.0,
        },
        {
            "name": "gujarat_plains",
            "center_lat": 22.30,
            "center_lon": 72.20,
            "radius_km": 320.0,
            "direction_from_deg": 280.0,
            "speed_kmh": 12.0,
        },
        {
            "name": "rajasthan_aravalli",
            "center_lat": 26.90,
            "center_lon": 75.80,
            "radius_km": 340.0,
            "direction_from_deg": 300.0,
            "speed_kmh": 13.0,
        },
        {
            "name": "gangetic_plain_east",
            "center_lat": 25.60,
            "center_lon": 85.10,
            "radius_km": 380.0,
            "direction_from_deg": 280.0,
            "speed_kmh": 10.0,
        },
        {
            "name": "vidarbha",
            "center_lat": 21.10,
            "center_lon": 79.10,
            "radius_km": 300.0,
            "direction_from_deg": 275.0,
            "speed_kmh": 11.0,
        },
        {
            "name": "central_highlands",
            "center_lat": 23.30,
            "center_lon": 77.40,
            "radius_km": 340.0,
            "direction_from_deg": 265.0,
            "speed_kmh": 10.0,
        },
        {
            "name": "deccan_plateau",
            "center_lat": 17.40,
            "center_lon": 78.50,
            "radius_km": 420.0,
            "direction_from_deg": 260.0,
            "speed_kmh": 12.0,
        },
        {
            "name": "south_interior",
            "center_lat": 12.97,
            "center_lon": 77.59,
            "radius_km": 340.0,
            "direction_from_deg": 240.0,
            "speed_kmh": 9.0,
        },
        {
            "name": "tamil_nadu_cauvery",
            "center_lat": 13.10,
            "center_lon": 80.30,
            "radius_km": 320.0,
            "direction_from_deg": 100.0,
            "speed_kmh": 11.0,
        },
        {
            "name": "bengal_delta",
            "center_lat": 22.60,
            "center_lon": 88.40,
            "radius_km": 320.0,
            "direction_from_deg": 190.0,
            "speed_kmh": 8.0,
        },
        {
            "name": "odisha_coast",
            "center_lat": 20.30,
            "center_lon": 85.80,
            "radius_km": 280.0,
            "direction_from_deg": 200.0,
            "speed_kmh": 10.0,
        },
        {
            "name": "north_east",
            "center_lat": 26.10,
            "center_lon": 91.70,
            "radius_km": 420.0,
            "direction_from_deg": 270.0,
            "speed_kmh": 9.0,
        },
        {
            "name": "kashmir_valley",
            "center_lat": 34.10,
            "center_lon": 74.80,
            "radius_km": 260.0,
            "direction_from_deg": 300.0,
            "speed_kmh": 7.0,
        },
    ]
}


def generate_json() -> None:
    fire_path = DATA_DIR / "fire_hotspots_mock.json"
    fire_path.write_text(json.dumps(FIRE_HOTSPOTS, indent=2), encoding="utf-8")
    print(f"wrote {fire_path} ({len(FIRE_HOTSPOTS['hotspots'])} hotspots)")
    wind_path = DATA_DIR / "wind_data_mock.json"
    wind_path.write_text(json.dumps(WIND_DATA, indent=2), encoding="utf-8")
    print(f"wrote {wind_path} ({len(WIND_DATA['regions'])} regions)")


if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    generate_csvs()
    generate_json()
    print("seed data generation complete")
