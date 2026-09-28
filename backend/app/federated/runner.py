"""FL orchestration (section 6).

Runs in a daemon thread; a module-level Lock plus a state flag guarantees only
one run at a time (a second POST while running returns "already running").
After each round, fl_status.json is written atomically (tmp + os.replace).
"""
import json
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import numpy as np
import torch

from ..config import (
    FL_BATCH_SIZE, FL_LOCAL_EPOCHS, FL_LR, FL_ROUNDS, MIN_TRAIN_WINDOWS, SEED,
)
from .client import FLClient
from .evaluate import evaluate_and_write
from .model import get_parameters, seed_everything, set_parameters
from .server import aggregate_round_results

logger = logging.getLogger("vayusetu.runner")

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed")
STATUS_PATH = os.path.join(PROCESSED_DIR, "fl_status.json")
MODEL_PATH = os.path.join(PROCESSED_DIR, "global_model.pt")

_STATUS_LOCK = threading.Lock()
_RUN_LOCK = threading.Lock()
_state: dict = {
    "running": False,
    "status": "idle",  # idle | running | completed | failed
    "error": None,
}

IDLE_STATUS = {
    "status": "idle",
    "rounds": [],
    "total_rounds": FL_ROUNDS,
    "clients": [],
    "excluded": [],
    "started_at": None,
    "completed_at": None,
    "error": None,
}


def _write_status_atomic(status: dict) -> None:
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    tmp = STATUS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2)
    os.replace(tmp, STATUS_PATH)


def read_status() -> dict:
    """API-facing read: missing or corrupt file returns the idle default."""
    with _STATUS_LOCK:
        try:
            with open(STATUS_PATH, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return dict(IDLE_STATUS)
            return data
        except Exception:
            return dict(IDLE_STATUS)


def is_running() -> bool:
    return _state["running"]


def load_global_model() -> tuple[str | None, list | None]:
    """Returns (model_version, params) if a saved global model exists."""
    try:
        payload = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
        params = [t.numpy().astype("float32") for t in payload.get("params", [])]
        return payload.get("model_version"), params
    except Exception:
        return None, None


def save_global_model(params: list) -> str:
    model_version = "fedavg-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    # Store plain tensors (weights_only-safe loading).
    tensors = [torch.tensor(np.asarray(p), dtype=torch.float32) for p in params]
    torch.save({"model_version": model_version, "params": tensors}, MODEL_PATH)
    return model_version


def model_version() -> str | None:
    version, _ = load_global_model()
    return version


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_clients(store) -> tuple[list[FLClient], list[dict], dict[str, np.ndarray]]:
    """One FLClient per participating tier-1 city; excluded cities get a reason.

    last_aqi_by_client maps city_id -> scaled aqi(t) per validation sample
    (for the persistence baseline, computed from the same windows).
    """
    from ..data.features import AQI_SCALE, build_windows, chronological_split, city_frame

    clients: list[FLClient] = []
    excluded: list[dict] = []
    last_aqi_by_client: dict[str, np.ndarray] = {}

    tier1 = [c for c in store.active_cities() if store.tier_of(c.city_id) == 1]
    for entry in tier1:
        g = city_frame(store.master, entry.city_id)
        if g.empty:
            excluded.append({"city_id": entry.city_id, "reason": "no data rows"})
            continue
        X, y, end_dates = build_windows(g)
        if X.shape[0] < MIN_TRAIN_WINDOWS:
            excluded.append({"city_id": entry.city_id, "reason": f"only {X.shape[0]} training windows"})
            continue
        X_train, y_train, X_val, y_val = chronological_split(X, y)
        clients.append(FLClient(
            entry.city_id, X_train, y_train, X_val, y_val,
            seed=SEED, batch_size=FL_BATCH_SIZE, lr=FL_LR, local_epochs=FL_LOCAL_EPOCHS,
        ))
        # aqi(t) per validation sample: the observed AQI on each window's last
        # input day, scaled — this is what persistence predicts for all horizons.
        aqi_series = g["aqi"]
        vals = []
        for d in end_dates:
            v = aqi_series.loc[d] if d in aqi_series.index else np.nan
            vals.append(float(v) / AQI_SCALE if v == v else 0.0)
        last_aqi_by_client[entry.city_id] = np.asarray(vals, dtype=float)

    return clients, excluded, last_aqi_by_client


def run_training(store, done_callback=None) -> None:
    """Blocking full run; called on the daemon thread. Do not call from a request."""
    global _state
    with _RUN_LOCK:
        if _state["running"]:
            return
        _state["running"] = True
        _state["status"] = "running"
        _state["error"] = None

    status: dict = {
        "status": "running",
        "rounds": [],
        "total_rounds": FL_ROUNDS,
        "clients": [],
        "excluded": [],
        "started_at": _utcnow(),
        "completed_at": None,
        "error": None,
    }
    try:
        # One intra-op thread per torch process: the GRU is tiny, so per-op
        # parallelism only adds contention. Parallelism comes from running
        # several clients at once instead.
        torch.set_num_threads(1)
        seed_everything(SEED)

        clients, excluded, last_aqi_by_client = _build_clients(store)
        status["clients"] = [c.city_id for c in clients]
        status["excluded"] = excluded
        if not clients:
            raise RuntimeError("no city has enough training windows to participate")
        _write_status_atomic(status)

        # Same initial weights for every party (section 6).
        from .model import build_model

        init_params = get_parameters(build_model(SEED))

        rounds = []
        global_params = init_params
        # Clients train in parallel threads: each client owns its own model and
        # arrays (no shared mutable state), torch releases the GIL in its
        # kernels, and results are collected in client order so the run stays
        # fully deterministic.
        max_workers = min(8, len(clients))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            for round_num in range(1, FL_ROUNDS + 1):
                futures = [pool.submit(c.fit, global_params) for c in clients]
                fit_results = []
                for client, fut in zip(clients, futures):
                    params, n_train, train_loss = fut.result()
                    fit_results.append((client.city_id, params, n_train, train_loss))

                global_params, client_losses = aggregate_round_results(fit_results)

                # All clients evaluate the new global params (parallel, in order).
                val_futures = [pool.submit(c.evaluate, global_params) for c in clients]
                val_losses, maes = [], []
                for fut in val_futures:
                    mse, mae_aqi, n_val = fut.result()
                    val_losses.append((mse, n_val))
                    maes.append((mae_aqi, n_val))

                total_val = sum(n for _, n in val_losses)
                global_loss = float(sum(l * n for l, n in val_losses) / total_val)
                n_h = len(maes[0][0])
                global_val_mae = float(
                    sum(sum(m) * n for m, n in maes) / (total_val * n_h)
                )
                rounds.append({
                    "round": round_num,
                    "client_losses": client_losses,
                    "global_loss": round(global_loss, 6),
                    "global_val_mae": round(global_val_mae, 1),
                })
                status["rounds"] = rounds
                _write_status_atomic(status)
                logger.info("FL round %d/%d: global_loss=%.6f val_mae=%.1f",
                            round_num, FL_ROUNDS, global_loss, global_val_mae)

        model_version_str = save_global_model(global_params)
        # model_version is served from global_model.pt via /api/meta; the status
        # file keeps exactly the FlStatus key set (section 11.2).

        # Residual p90 per horizon on the pooled validation set (section 7).
        residual_p90 = _residual_p90(clients, global_params)

        name_by_id = {c.city_id: c.name for c in store.cities}
        evaluate_and_write(clients, global_params, last_aqi_by_client, residual_p90,
                           name_by_id=name_by_id)

        status["status"] = "completed"
        status["completed_at"] = _utcnow()
        _write_status_atomic(status)
        if done_callback:
            done_callback(model_version_str)
        logger.info("FL run completed: model %s", model_version_str)
    except Exception as exc:
        status["status"] = "failed"
        status["error"] = str(exc)
        status["completed_at"] = _utcnow()
        _write_status_atomic(status)
        logger.exception("FL run failed")
    finally:
        with _RUN_LOCK:
            _state["running"] = False
            _state["status"] = status.get("status", "failed")


def _residual_p90(clients: list[FLClient], global_params: list) -> list[float]:
    """90th percentile of |residual| per horizon on the pooled validation set."""
    import torch as _torch
    from torch import nn

    model = clients[0].model  # any client model works as a carrier
    set_parameters(model, global_params)
    model.eval()
    per_horizon: dict[int, list[float]] = {}
    with _torch.no_grad():
        for client in clients:
            pred = model(_torch.from_numpy(client.X_val))
            target = _torch.from_numpy(client.y_val)
            abs_res = (pred - target).abs() * 500.0
            for h in range(abs_res.shape[1]):
                per_horizon.setdefault(h, []).extend(abs_res[:, h].tolist())
    return [float(np.percentile(per_horizon[h], 90)) for h in sorted(per_horizon)]


def start_run_async(store, done_callback=None) -> bool:
    """Starts a training run on a daemon thread. Returns False if already running."""
    with _RUN_LOCK:
        if _state["running"]:
            return False
        t = threading.Thread(target=run_training, args=(store, done_callback), daemon=True)
        t.start()
        return True
