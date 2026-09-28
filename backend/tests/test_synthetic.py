"""Synthetic generator tests (section 14.4): determinism + Delhi episode."""
import os
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR)) if str(BACKEND_DIR) not in sys.path else None


def _generate():
    from app.data import synthetic
    from app.data.registry import load_cities

    cities = load_cities()
    return synthetic.generate(cities)


def test_two_runs_identical():
    m1, f1 = _generate()
    m2, f2 = _generate()
    assert m1.equals(m2)
    assert f1.equals(f2)


def test_delhi_severe_episode_last_10_days():
    from app.services.aqi import compute_aqi

    master, _ = _generate()
    delhi = master[master["city_id"] == "delhi"].sort_values("date").tail(10)
    aqis = []
    for _, r in delhi.iterrows():
        aqi = compute_aqi(float(r["pm25"]), float(r["pm10"]))
        aqis.append(aqi)
    days_above_300 = sum(1 for a in aqis if a is not None and a > 300)
    assert days_above_300 >= 3, f"only {days_above_300} days above 300: {aqis}"


def test_roles_respected():
    master, _ = _generate()
    # aux_only cities have no pollutant columns.
    varanasi = master[master["city_id"] == "varanasi"]
    assert len(varanasi) > 0
    assert varanasi["aqi"].isna().all()
    assert varanasi["temp"].notna().all()
    # none-role cities have no rows at all.
    assert len(master[master["city_id"] == "gorakhpur"]) == 0
    # skip cities are not generated.
    assert len(master[master["city_id"] == "shillong"]) == 0


def test_fires_written_with_source():
    _, fires = _generate()
    assert {"date", "latitude", "longitude", "frp", "source"}.issubset(fires.columns)
    assert (fires["source"] == "synthetic").all()
    assert len(fires) > 0
