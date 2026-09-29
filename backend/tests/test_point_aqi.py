"""Point AQI tests (section 14, item 9)."""
import math

from fastapi.testclient import TestClient

from app.main import app
from app.services.point_aqi_service import estimate_point_aqi, outside_india
from app.store import DataStore


def test_outside_india_is_flagged_not_raised():
    assert outside_india(40.0, 77.0) is True       # north of the box
    assert outside_india(20.0, 100.0) is True      # east of the box
    assert outside_india(28.6139, 77.2090) is False  # Delhi


def test_endpoint_outside_india_returns_200_envelope():
    with TestClient(app) as client:
        r = client.get("/api/aqi", params={"latitude": 40.0, "longitude": 77.0})
        assert r.status_code == 200
        body = r.json()
        assert body.get("error") is True
        assert "outside India" in body.get("message", "")


def test_endpoint_on_tier1_city_close_to_latest_aqi():
    # Isolate the IDW math from citizen-report blending: startup seeds reports
    # and other tests drop reports near Delhi, and the blend (by design) pulls
    # the estimate toward them. Clear AFTER startup so seeding has already run.
    from sqlmodel import delete

    from app.db import get_session
    from app.tables import CitizenReportRow

    with TestClient(app) as client:
        with get_session() as session:
            session.exec(delete(CitizenReportRow))
            session.commit()
        cities = client.get("/api/cities").json()["cities"]
        delhi = next(c for c in cities if c["city_id"] == "delhi")
        r = client.get("/api/aqi", params={"latitude": delhi["latitude"], "longitude": delhi["longitude"]})
        assert r.status_code == 200
        body = r.json()
        assert not body.get("error")
        assert body["method"] == "idw_point_interpolation"
        # IDW with the 10 km floor lets nearer neighbours pull the estimate a
        # little; 25 AQI points still proves the point tracks ground truth.
        assert abs(body["estimated_aqi"] - delhi["latest_aqi"]) <= 25.0
        assert body["confidence"] > 0.7
        assert body["nearest_city_id"] == "delhi"
        assert body["nearby_reports_considered"] >= 0


def test_remote_point_still_returns_number_with_low_confidence():
    with TestClient(app) as client:
        # Deep in the Thar desert, far from any tier-1 city.
        r = client.get("/api/aqi", params={"latitude": 27.0, "longitude": 70.5})
        assert r.status_code == 200
        body = r.json()
        assert not body.get("error")
        assert isinstance(body["estimated_aqi"], (int, float))
        assert not math.isnan(body["estimated_aqi"])
        assert body["confidence"] < 0.4


def test_nearest_city_math_is_sort_independent():
    store = DataStore.instance()
    a = estimate_point_aqi(store, 25.0, 80.0)
    # Shuffle the registry order and recompute.
    store.cities.reverse()
    try:
        b = estimate_point_aqi(store, 25.0, 80.0)
    finally:
        store.cities.reverse()
    assert a["estimated_aqi"] == b["estimated_aqi"]
    assert a["nearest_city_id"] == b["nearest_city_id"]


def test_between_two_cities_confidence_midrange():
    with TestClient(app) as client:
        # A point roughly between Delhi and Jaipur.
        r = client.get("/api/aqi", params={"latitude": 27.8, "longitude": 76.4})
        body = r.json()
        assert not body.get("error")
        assert 0.15 <= body["confidence"] <= 0.95
        assert len(body["contributing_cities"]) >= 2
        assert body["contributing_cities"][0]["weight"] >= body["contributing_cities"][-1]["weight"]
