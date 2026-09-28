"""API contract tests (section 14.7): every endpoint, exact keys, no NaN.

ASSUMPTION: contract tests share one app instance per module (TestClient
startup loads the real dataset once; per-test DB rows are cleaned).
"""
import json
import math

import pytest


def _no_nan(obj, path="$"):
    if isinstance(obj, float):
        assert not math.isnan(obj), f"NaN at {path}"
        assert not math.isinf(obj), f"Inf at {path}"
    elif isinstance(obj, dict):
        for k, v in obj.items():
            _no_nan(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _no_nan(v, f"{path}[{i}]")


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_meta_contract(client):
    r = client.get("/api/meta")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {
        "data_mode", "fallback_reason", "demo_now", "n_cities",
        "n_tier1", "n_tier2", "n_tier3", "model_version", "model_method", "fl_status",
    }
    assert body["data_mode"] in ("synthetic", "real")
    assert body["model_method"] in ("federated_gru", "persistence")
    assert body["fl_status"] in ("idle", "running", "completed", "failed")
    assert body["n_cities"] == body["n_tier1"] + body["n_tier2"] + body["n_tier3"]
    assert body["n_cities"] == 28  # synthetic-mode definition of done
    assert body["n_tier1"] == 20 and body["n_tier2"] == 5 and body["n_tier3"] == 3
    _no_nan(body)


def test_cities_contract(client):
    r = client.get("/api/cities")
    assert r.status_code == 200
    cities = r.json()["cities"]
    assert len(cities) == 28
    keys = {"city_id", "name", "state", "latitude", "longitude", "tier",
            "latest_aqi", "latest_date", "citizen_adjusted_aqi", "report_count_24h"}
    for c in cities:
        assert set(c) == keys
        assert c["tier"] in (1, 2, 3)
        assert c["report_count_24h"] >= 0
    names = [c["name"] for c in cities]
    assert names == sorted(names)  # sorted by name
    _no_nan(cities)


def test_city_history_contract(client):
    r = client.get("/api/cities/delhi/history?days=10")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"city_id", "points"}
    assert body["city_id"] == "delhi"
    assert len(body["points"]) == 10
    for p in body["points"]:
        assert set(p) == {"date", "aqi", "pm25"}
    _no_nan(body)
    # Validation bounds on days.
    assert client.get("/api/cities/delhi/history?days=0").status_code == 422
    assert client.get("/api/cities/delhi/history?days=366").status_code == 422
    assert client.get("/api/cities/delhi/history?days=abc").status_code == 422


def test_city_history_unknown_city_404_envelope(client):
    r = client.get("/api/cities/not_a_city/history")
    assert r.status_code == 404
    body = r.json()
    assert body["error"] is True
    assert isinstance(body["message"], str)


def test_reports_contract_and_flow(client):
    # Seed reports exist from startup.
    r = client.get("/api/reports")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"reports"}
    keys = {"id", "latitude", "longitude", "city_id", "haze_score", "confidence",
            "trust_weight", "source", "created_at"}
    for rep in body["reports"]:
        assert set(rep) == keys
        assert rep["source"] in ("user", "seed")
    _no_nan(body)

    # Manual submission round trip.
    r = client.post("/api/reports", json={
        "latitude": 28.6139, "longitude": 77.2090, "manual_visibility": "hazy",
    })
    assert r.status_code == 201
    result = r.json()
    assert set(result) == {"id", "city_id", "haze_score", "confidence", "trust_weight", "scorer"}
    assert result["city_id"] == "delhi"  # server-side assignment
    assert result["scorer"] == "manual"

    # city_id filter.
    r = client.get("/api/reports?city_id=delhi")
    assert all(rep["city_id"] == "delhi" for rep in r.json()["reports"])


def test_report_validation_422(client):
    # Out of India (latitude below bbox).
    r = client.post("/api/reports", json={"latitude": 5.0, "longitude": 77.0, "manual_visibility": "hazy"})
    assert r.status_code == 422
    assert r.json()["error"] is True
    # Longitude out of bbox.
    r = client.post("/api/reports", json={"latitude": 20.0, "longitude": 99.0, "manual_visibility": "hazy"})
    assert r.status_code == 422
    # Neither photo nor visibility.
    r = client.post("/api/reports", json={"latitude": 28.6, "longitude": 77.2})
    assert r.status_code == 422
    # Bad base64.
    r = client.post("/api/reports", json={"latitude": 28.6, "longitude": 77.2, "photo_base64": "####"})
    assert r.status_code == 422
    assert r.json()["message"] == "could not read image"
    # Outside coverage (mid-Indian ocean, inside bbox but > 200 km from any city).
    r = client.post("/api/reports", json={"latitude": 8.0, "longitude": 93.5, "manual_visibility": "clear"})
    assert r.status_code == 422
    assert r.json()["message"] == "outside coverage"
    # Request-schema violation also uses the envelope.
    r = client.post("/api/reports", json={"latitude": "not-a-number", "longitude": 77.2})
    assert r.status_code == 422
    body = r.json()
    assert body["error"] is True and isinstance(body["message"], str)


def test_photo_report_scorer_label(client):
    """A valid 1x1 PNG photo returns scorer=heuristic_v1."""
    import base64
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (64, 64), color=(180, 170, 160)).save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    r = client.post("/api/reports", json={
        "latitude": 28.6139, "longitude": 77.2090, "photo_base64": b64,
    })
    assert r.status_code == 201
    assert r.json()["scorer"] == "heuristic_v1"


def test_hotspots_contract(client):
    r = client.get("/api/hotspots")
    assert r.status_code == 200
    hotspots = r.json()["hotspots"]
    keys = {"id", "latitude", "longitude", "cause", "confidence", "detected_on", "frp",
            "wind_direction_deg", "wind_speed_ms", "wind_toward_deg",
            "downwind_city_id", "downwind_city_name", "distance_km", "eta_hours"}
    assert len(hotspots) > 0
    for h in hotspots:
        assert set(h) == keys
        assert h["cause"] in ("stubble_burning", "open_burning", "industrial")
    # Definition of done: at least one downwind hit with ETA.
    assert any(h["downwind_city_id"] and h["eta_hours"] is not None for h in hotspots)
    _no_nan(hotspots)


def test_forecast_contract_all_active_cities(client):
    r = client.get("/api/cities")
    cities = r.json()["cities"]
    interp_count = 0
    for c in cities:
        r = client.get(f"/api/forecast?city_id={c['city_id']}")
        assert r.status_code == 200, (c["city_id"], r.text)
        body = r.json()
        if body.get("error"):
            # Only allowed error: no monitored city within radius (tier 2/3 remote).
            assert "no monitored city within" in body["message"]
            continue
        assert set(body) == {"city_id", "tier", "method", "model_version", "points"}
        assert body["method"] in ("federated_gru", "persistence", "neighbor_idw")
        assert body["method"] != "neighbor_idw" or c["tier"] in (2, 3)
        if body["method"] == "neighbor_idw":
            interp_count += 1
        assert len(body["points"]) == 4
        for p in body["points"]:
            assert set(p) == {"date", "horizon_days", "predicted_aqi", "lower_bound", "upper_bound", "observed"}
            assert p["horizon_days"] in (0, 1, 2, 3)
            assert 0.0 <= p["predicted_aqi"] <= 500.0
            assert p["lower_bound"] <= p["predicted_aqi"] <= p["upper_bound"]
        _no_nan(body)
    assert interp_count >= 1  # tier 2/3 cities are interpolated


def test_forecast_unknown_city_404_envelope(client):
    r = client.get("/api/forecast?city_id=not_a_city")
    assert r.status_code == 404
    assert r.json()["error"] is True


def test_forecast_requires_city(client):
    r = client.get("/api/forecast")
    assert r.status_code == 422
    assert r.json()["error"] is True


def test_alerts_flow_contract(client):
    r = client.post("/api/alerts/check")
    assert r.status_code == 200
    assert set(r.json()) == {"created"}
    assert r.json()["created"] >= 1  # synthetic data guarantees threshold crossings

    r = client.get("/api/alerts")
    alerts = r.json()["alerts"]
    keys = {"id", "city_id", "city_name", "severity", "predicted_aqi", "forecast_date",
            "action_framework", "grap_stage", "action", "channels", "created_at", "acknowledged"}
    assert len(alerts) >= 1
    tier1_ids = {"delhi", "gurugram"}
    ncr_alert = None
    non_ncr_alert = None
    for a in alerts:
        assert set(a) == keys
        assert a["severity"] in ("Poor", "Very Poor", "Severe")
        assert a["action_framework"] in ("GRAP", "ADVISORY")
        assert a["action_framework"] != "GRAP" or a["grap_stage"] is not None
        assert isinstance(a["action"], str) and len(a["action"]) > 0
        assert a["channels"] == ["dashboard"] or a["channels"] == ["dashboard", "sms_simulated"]
        if a["city_id"] in tier1_ids:
            ncr_alert = a
            assert a["action_framework"] == "GRAP"
        else:
            non_ncr_alert = a
            assert a["action_framework"] == "ADVISORY" and a["grap_stage"] is None
    _no_nan(alerts)

    # Idempotency: a second check without acks creates nothing new.
    r2 = client.post("/api/alerts/check")
    assert r2.json()["created"] == 0

    # Acknowledge updates state; unknown id 404s with the envelope.
    target = alerts[0]
    r = client.post(f"/api/alerts/{target['id']}/acknowledge")
    assert r.status_code == 200
    assert r.json() == {"id": target["id"], "acknowledged": True}
    r = client.get("/api/alerts")
    updated = next(a for a in r.json()["alerts"] if a["id"] == target["id"])
    assert updated["acknowledged"] is True
    r = client.post("/api/alerts/999999/acknowledge")
    assert r.status_code == 404
    assert r.json()["error"] is True


def test_federated_status_contract(client):
    r = client.get("/api/federated/status")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"status", "rounds", "total_rounds", "clients", "excluded",
                         "started_at", "completed_at", "error"}
    assert body["status"] in ("idle", "running", "completed", "failed")
    assert body["total_rounds"] == 8
    _no_nan(body)


def test_federated_eval_contract_before_run(client):
    r = client.get("/api/federated/eval")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"available", "rows", "mean_mae_persistence",
                         "mean_mae_local", "mean_mae_federated", "mean_mae_personalized"}
    if not body["available"]:
        assert body["rows"] == []
    _no_nan(body)


def test_unknown_route_404_envelope(client):
    r = client.get("/api/definitely_not_a_route")
    assert r.status_code == 404
    body = r.json()
    assert body["error"] is True
    assert isinstance(body["message"], str)
