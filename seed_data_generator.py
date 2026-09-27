"""Deterministic seed data generator for VayuSetu.

Produces (under backend/data/):
  - historical_aqi_{delhi,kanpur,pune}.csv : 90 days of synthetic hourly AQI
    with diurnal + weekly seasonality and noise, seeded with np.random.seed(42)
    so re-running setup never changes the demo's charts.
  - fire_hotspots_mock.json : fixed stubble-burning points near Punjab/Haryana
    and industrial points near Kanpur.
  - wind_data_mock.json : fixed per-region wind direction/speed so that at
    least two hotspots plausibly point toward Delhi/Kanpur with an ETA.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent / "backend" / "data"

CITY_PARAMS = {
    "delhi": {"base": 190.0, "amp": 55.0, "weekly": 18.0, "noise": 14.0},
    "kanpur": {"base": 155.0, "amp": 45.0, "weekly": 15.0, "noise": 12.0},
    "pune": {"base": 90.0, "amp": 30.0, "weekly": 10.0, "noise": 9.0},
}

START = pd.Timestamp("2026-06-01 00:00:00")
HOURS = 90 * 24


def generate_csvs() -> None:
    np.random.seed(42)
    hours = pd.date_range(START, periods=HOURS, freq="h")
    hod = hours.hour.to_numpy(dtype=float)
    dow = hours.dayofweek.to_numpy(dtype=float)

    for city, p in CITY_PARAMS.items():
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
        out = DATA_DIR / f"historical_aqi_{city}.csv"
        df.to_csv(out, index=False)
        print(f"wrote {out} ({len(df)} rows)")


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
    ]
}


def generate_json() -> None:
    fire_path = DATA_DIR / "fire_hotspots_mock.json"
    fire_path.write_text(json.dumps(FIRE_HOTSPOTS, indent=2), encoding="utf-8")
    print(f"wrote {fire_path}")
    wind_path = DATA_DIR / "wind_data_mock.json"
    wind_path.write_text(json.dumps(WIND_DATA, indent=2), encoding="utf-8")
    print(f"wrote {wind_path}")


if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    generate_csvs()
    generate_json()
    print("seed data generation complete")
