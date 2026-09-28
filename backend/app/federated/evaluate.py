"""Baselines and honest comparison (section 6, FlEval in 11.2).

- persistence: predict aqi(t) for all three horizons; MAE on each city's val set.
- local-only: same architecture, same initial weights, trained on that city
  alone for FL_ROUNDS * FL_LOCAL_EPOCHS epochs.
- federated: the global model's MAE on the same validation set.

Results are reported exactly as measured. Nothing here is tuned to make
federated win — if it loses somewhere, that row simply shows it.
"""
import json
import logging
import math
import os
import threading
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import torch
from torch import nn

from ..config import FL_LOCAL_EPOCHS, FL_ROUNDS, HORIZONS
from .client import FLClient
from .model import build_model, get_parameters, set_parameters

logger = logging.getLogger("vayusetu.evaluate")

EVAL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed", "fl_eval.json")

# Model creation draws from torch's GLOBAL RNG, so parallel threads building
# models would interleave draws and change every initialisation. Serialising
# model construction keeps the baselines deterministic; training itself stays
# parallel (it consumes only per-client local generators).
_INIT_LOCK = threading.Lock()


def _mae_per_horizon(model: nn.Module, X: np.ndarray, y: np.ndarray) -> tuple[list[float], int]:
    model.eval()
    with torch.no_grad():
        pred = model(torch.from_numpy(X.astype(np.float32)))
        target = torch.from_numpy(y.astype(np.float32))
        mae = (pred - target).abs().mean(dim=0) * 500.0
    return [float(v) for v in mae], int(X.shape[0])


def persistence_mae(y_val: np.ndarray, last_aqi: np.ndarray) -> list[float]:
    """y_val: (N, H) scaled targets; last_aqi: (N,) scaled aqi(t)."""
    n_h = y_val.shape[1]
    return [float(np.mean(np.abs(y_val[:, h] - last_aqi)) * 500.0) for h in range(n_h)]


def evaluate_and_write(
    clients: list[FLClient],
    global_params: list,
    last_aqi_by_client: dict[str, np.ndarray],
    residual_p90_by_horizon: list[float] | None = None,
    name_by_id: dict[str, str] | None = None,
) -> dict:
    """Computes all baselines + federated MAE per city and writes fl_eval.json."""
    rows = []
    n_h = len(HORIZONS)
    names = name_by_id or {}

    def _baseline_for(client: FLClient) -> tuple:
        """All baselines for one client. Runs in a worker thread; the client
        owns every array and model it touches, so this is thread-safe."""
        # Local-only: train from the same seeded init on this city alone.
        with _INIT_LOCK:
            local_model = build_model(client.seed)
        opt = torch.optim.Adam(local_model.parameters(), lr=client.lr)
        X = torch.from_numpy(client.X_train)
        y = torch.from_numpy(client.y_train)
        gen = torch.Generator().manual_seed(client.seed)
        for _epoch in range(FL_ROUNDS * FL_LOCAL_EPOCHS):
            local_model.train()
            order = torch.randperm(X.shape[0], generator=gen)
            for start in range(0, X.shape[0], client.batch_size):
                idx = order[start:start + client.batch_size]
                opt.zero_grad()
                loss = nn.functional.mse_loss(local_model(X[idx.numpy()]), y[idx.numpy()])
                loss.backward()
                opt.step()

        mae_local, n_val = _mae_per_horizon(local_model, client.X_val, client.y_val)

        # Persistence: aqi(t) repeated for every horizon. The last_aqi series
        # covers ALL windows chronologically; validation is the last n_val of
        # them (the chronological split), so slice the tail.
        last_scaled = last_aqi_by_client.get(client.city_id)
        if last_scaled is not None and len(last_scaled) >= client.n_val():
            mae_persist = persistence_mae(client.y_val, last_scaled[-client.n_val():])
        else:
            mae_persist = [float("nan")] * n_h

        # Federated: the global model on this city's validation set.
        set_parameters(local_model, global_params)
        mae_fed, _ = _mae_per_horizon(local_model, client.X_val, client.y_val)

        # Personalized: from the final global parameters, fine-tune 2 local
        # epochs on this city's own data only (nothing is sent anywhere) —
        # a standard federated-learning finding worth reporting.
        opt_p = torch.optim.Adam(local_model.parameters(), lr=client.lr)
        for _epoch in range(client.local_epochs):
            local_model.train()
            order = torch.randperm(X.shape[0], generator=gen)
            for start in range(0, X.shape[0], client.batch_size):
                idx = order[start:start + client.batch_size]
                opt_p.zero_grad()
                loss = nn.functional.mse_loss(local_model(X[idx.numpy()]), y[idx.numpy()])
                loss.backward()
                opt_p.step()
        mae_personalized, _ = _mae_per_horizon(local_model, client.X_val, client.y_val)
        return client, mae_persist, mae_local, mae_fed, mae_personalized, n_val

    with ThreadPoolExecutor(max_workers=min(8, len(clients))) as pool:
        for client, mae_persist, mae_local, mae_fed, mae_personalized, n_val in pool.map(_baseline_for, clients):
            def _mean(vals: list[float]) -> float:
                clean = [v for v in vals if not math.isnan(v)]
                return float(np.mean(clean)) if clean else float("nan")

            rows.append({
                "city_id": client.city_id,
                "name": names.get(client.city_id, client.city_id),
                "n_val": n_val,
                "mae_persistence": round(_mean(mae_persist), 1),
                "mae_local": round(_mean(mae_local), 1),
                "mae_federated": round(_mean(mae_fed), 1),
                "mae_personalized": round(_mean(mae_personalized), 1),
            })
            # Per-horizon detail is logged, not shipped.
            logger.info("%s MAE per horizon - persistence %s local %s federated %s personalized %s",
                        client.city_id,
                        [round(v, 1) for v in mae_persist],
                        [round(v, 1) for v in mae_local],
                        [round(v, 1) for v in mae_fed],
                        [round(v, 1) for v in mae_personalized])

    def _overall(key: str) -> float | None:
        vals = [r[key] for r in rows if not math.isnan(r[key])]
        if not vals:
            return None
        w = [r["n_val"] for r in rows if not math.isnan(r[key])]
        return round(float(np.average(vals, weights=w)), 1)

    payload = {
        "available": len(rows) > 0,
        "rows": rows,
        "mean_mae_persistence": _overall("mae_persistence"),
        "mean_mae_local": _overall("mae_local"),
        "mean_mae_federated": _overall("mae_federated"),
        "mean_mae_personalized": _overall("mae_personalized"),
    }
    if residual_p90_by_horizon is not None:
        payload["residual_p90_by_horizon"] = [round(float(v), 1) for v in residual_p90_by_horizon]
    # The FlEval contract allows exactly six keys per row; drop the internal
    # per-horizon breakdown before writing.

    os.makedirs(os.path.dirname(EVAL_PATH), exist_ok=True)
    tmp_path = EVAL_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    os.replace(tmp_path, EVAL_PATH)
    logger.info("wrote fl_eval.json: federated mean MAE %s vs persistence %s, local-only %s",
                payload["mean_mae_federated"], payload["mean_mae_persistence"], payload["mean_mae_local"])
    return payload


def load_eval() -> dict | None:
    """Read fl_eval.json; a corrupt file is treated as absent (section 12)."""
    try:
        with open(EVAL_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return None
        return data
    except Exception:
        return None
