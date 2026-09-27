"""Flower server side: FedAvg strategy that records round-by-round losses to
status.json (atomic write) so GET /api/federated/status can serve them.

DEMO NOTE: global_loss is the average of each city's LOCAL validation loss,
evaluated with the freshly-aggregated global model. That is exactly what
federated evaluation computes (an average of local losses) — raw city data is
never pooled into one training set; the evaluation here happens inside the
simulation process purely to produce the demo's convergence curve.
"""
import json
import logging
import os
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from flwr.common import Parameters, parameters_to_ndarrays
from flwr.server.strategy import FedAvg

from ..config import DATA_DIR
from .model import AQI_SCALE, INPUT_LEN, AQIMLP, set_params

logger = logging.getLogger("vayusetu.fl.server")

STATUS_PATH = Path(__file__).resolve().parent / "status.json"
VAL_FRACTION = 0.2


def atomic_write_json(path: Path, payload: dict) -> None:
    """Write to a temp file then rename — guards against the API reading a
    half-written file mid-training (real race condition, explicitly avoided)."""
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    os.replace(tmp, path)


class StatusRecorder:
    def __init__(self, path: Path = STATUS_PATH):
        self.path = path
        self._val_sets: dict[str, tuple[torch.Tensor, torch.Tensor]] = {}

    def read(self) -> dict:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"status": "idle", "rounds": [], "started_at": None, "completed_at": None}

    def write(self, payload: dict) -> None:
        try:
            atomic_write_json(self.path, payload)
        except Exception as exc:
            logger.warning("could not write status.json: %s", exc)

    def record_round(self, round_number: int, client_losses: dict, global_loss: float) -> None:
        st = self.read()
        rounds = [r for r in st.get("rounds", []) if r.get("round") != round_number]
        rounds.append({"round": int(round_number), "client_losses": client_losses, "global_loss": float(global_loss)})
        rounds.sort(key=lambda r: r["round"])
        st["rounds"] = rounds
        st["status"] = "running"
        self.write(st)

    def validation_set(self, city: str):
        """Last 20% of each city's windows — same split the clients hold out."""
        if city not in self._val_sets:
            df = pd.read_csv(DATA_DIR / f"historical_aqi_{city}.csv")
            aqi = df["aqi"].to_numpy(dtype=np.float32) / AQI_SCALE
            xs, ys = [], []
            for i in range(INPUT_LEN, len(aqi)):
                xs.append(aqi[i - INPUT_LEN:i])
                ys.append(aqi[i])
            X = np.asarray(xs, dtype=np.float32)
            y = np.asarray(ys, dtype=np.float32)
            split = int(len(X) * (1 - VAL_FRACTION))
            self._val_sets[city] = (torch.from_numpy(X[split:]), torch.from_numpy(y[split:]).unsqueeze(1))
        return self._val_sets[city]

    def evaluate_global(self, parameters: Parameters) -> float:
        model = AQIMLP()
        set_params(model, parameters_to_ndarrays(parameters))
        model.eval()
        losses = []
        with torch.no_grad():
            for city in ("delhi", "kanpur", "pune"):
                X, y = self.validation_set(city)
                losses.append(float(torch.nn.functional.mse_loss(model(X), y)))
        return float(np.mean(losses)) if losses else 0.0


class RecordingFedAvg(FedAvg):
    """FedAvg + per-round loss recording for the demo UI."""

    def __init__(self, recorder: StatusRecorder, **kwargs):
        super().__init__(**kwargs)
        self.recorder = recorder

    def aggregate_fit(self, server_round, results, failures):
        # Signature matches flwr 1.11's FedAvg.aggregate_fit exactly.
        aggregated = super().aggregate_fit(server_round, results, failures)
        try:
            client_losses: dict[str, float] = {}
            for _, fit_res in results:
                metrics = fit_res.metrics or {}
                city = metrics.get("city")
                if city is not None:
                    client_losses[str(city)] = float(metrics.get("loss", 0.0))
            global_loss = self.recorder.evaluate_global(aggregated[0]) if aggregated[0] is not None else 0.0
            self.recorder.record_round(server_round, client_losses, global_loss)
        except Exception as exc:
            # Recording is for the UI only — never break training because of it.
            logger.warning("round %s recording failed: %s", server_round, exc)
        return aggregated
