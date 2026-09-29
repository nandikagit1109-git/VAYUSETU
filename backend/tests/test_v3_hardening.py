"""v3 hardening tests: alert dedupe (incl. acknowledged), rate limit, sources,
forecast_bounds.json, FL determinism hooks."""
import json

from fastapi.testclient import TestClient

from app.main import app
from app.services import alert_service


def test_alert_dedupe_includes_acknowledged():
    """Acknowledging an alert must stop the 30s check from recreating it."""
    with TestClient(app) as client:
        alerts = client.get("/api/alerts").json()["alerts"]
        assert alerts, "expected seeded/checked alerts"
        target = alerts[0]
        # Acknowledge the newest alert for its city+severity+forecast_date.
        r = client.post(f"/api/alerts/{target['id']}/acknowledge")
        assert r.status_code == 200

        created = client.post("/api/alerts/check").json()["created"]
        after = client.get("/api/alerts").json()["alerts"]
        same = [a for a in after
                if a["city_id"] == target["city_id"]
                and a["severity"] == target["severity"]
                and a["forecast_date"] == target["forecast_date"]]
        assert len(same) == 1, "acknowledged alert was recreated by /alerts/check"
        assert same[0]["acknowledged"] is True
        assert created == 0 or all(
            not (a["city_id"] == target["city_id"] and a["severity"] == target["severity"]
                 and a["forecast_date"] == target["forecast_date"])
            for a in after if a["id"] != target["id"]
        )


def test_report_rate_limit_429():
    with TestClient(app) as client:
        payload = {"latitude": 28.6139, "longitude": 77.2090, "manual_visibility": "hazy"}
        statuses = []
        for _ in range(22):
            r = client.post("/api/reports", json=payload)
            statuses.append(r.status_code)
            if r.status_code == 429:
                body = r.json()
                assert body.get("error") is True
                break
        assert 429 in statuses, "20/min rate limit never triggered"


def test_meta_has_sources():
    with TestClient(app) as client:
        meta = client.get("/api/meta").json()
        assert isinstance(meta.get("sources"), list)
        assert meta["sources"], "sources must describe actual data provenance"
        assert "Synthetic generator (seed 42)" in meta["sources"]


def test_forecast_bounds_file_written_after_training():
    import os

    from app.config import PROCESSED_DIR

    path = os.path.join(PROCESSED_DIR, "forecast_bounds.json")
    if not os.path.exists(path):
        # Trigger a run synchronously if no model has been trained yet.
        from app.federated import runner
        runner.run_training(app.dependency_overrides and __import__("app.store", fromlist=["DataStore"]).DataStore.instance())
    with open(path, encoding="utf-8") as f:
        bounds = json.load(f)
    assert set(bounds.keys()) == {"1", "2", "3"}
    assert all(isinstance(v, (int, float)) and v > 0 for v in bounds.values())


def test_fl_client_fit_uses_round_seed():
    """Same round index must reproduce the same shuffle and loss."""
    import numpy as np

    from app.federated.client import FLClient

    rng = np.random.default_rng(0)
    X = rng.normal(size=(50, 14, 23)).astype(np.float32)
    y = rng.normal(size=(50, 3)).astype(np.float32)
    c1 = FLClient("a", X, y, X[:10], y[:10], seed=42, client_index=0)
    c2 = FLClient("a", X, y, X[:10], y[:10], seed=42, client_index=0)
    p1, n1, l1 = c1.fit(None, round_index=3)
    p2, n2, l2 = c2.fit(None, round_index=3)
    assert n1 == n2 and abs(l1 - l2) < 1e-12
    assert all((a == b).all() for a, b in zip(p1, p2))
