"""Federated smoke test (section 14.6): 3 clients, 1 round, valid status file.

Uses synthetic in-memory windows so no heavy training runs here.
"""
import json
import os
import sys
from pathlib import Path

import numpy as np

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _toy_client(city_id: str, seed: int = 42):
    from app.federated.client import FLClient

    rng = np.random.default_rng(7)
    n = 80
    X = rng.normal(0, 0.5, size=(n, 14, 23)).astype(np.float32)
    y = rng.normal(0.3, 0.05, size=(n, 3)).astype(np.float32)
    return FLClient(city_id, X[:64], y[:64], X[64:], y[64:], seed=seed, local_epochs=1)


def test_three_clients_one_round(tmp_path, monkeypatch):
    from app.federated import runner

    status_path = tmp_path / "fl_status.json"
    monkeypatch.setattr(runner, "STATUS_PATH", str(status_path))
    monkeypatch.setattr(runner, "PROCESSED_DIR", str(tmp_path))
    monkeypatch.setattr(runner, "MODEL_PATH", str(tmp_path / "global_model.pt"))

    from app.federated.client import FLClient  # noqa: F401 (imports prove wiring)
    from app.federated.model import get_parameters, build_model
    from app.federated.server import aggregate_round_results

    clients = [_toy_client(f"city_{i}") for i in range(3)]
    global_params = get_parameters(build_model(42))

    fit_results = []
    for c in clients:
        params, n_train, loss = c.fit(global_params)
        fit_results.append((c.city_id, params, n_train, loss))
    new_global, client_losses = aggregate_round_results(fit_results)

    assert new_global is not None
    assert set(client_losses) == {"city_0", "city_1", "city_2"}
    for c in clients:
        mse, mae, n_val = c.evaluate(new_global)
        assert n_val == 16
        assert mse >= 0.0
        assert len(mae) == 3

    # Status-file round trip (atomic write + read).
    status = {
        "status": "completed", "rounds": [{"round": 1, "client_losses": client_losses,
                                            "global_loss": 0.01, "global_val_mae": 5.0}],
        "total_rounds": 1, "clients": [c.city_id for c in clients], "excluded": [],
        "started_at": "2025-11-30T00:00:00+00:00", "completed_at": "2025-11-30T00:00:01+00:00",
        "error": None,
    }
    runner._write_status_atomic(status)
    with open(status_path, encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["status"] == "completed"
    assert loaded["rounds"][0]["round"] == 1

    runner_read = runner.read_status.__wrapped__ if hasattr(runner.read_status, "__wrapped__") else None
    assert isinstance(loaded, dict)
