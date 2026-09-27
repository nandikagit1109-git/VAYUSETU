"""Flower client, parameterized by city name.

FEDERATION INVARIANT: each client loads ONLY its own city's CSV. Kanpur's
client never sees Delhi's rows — that is the whole point of the demo. No
cross-city data access exists anywhere in this file.
"""
import logging

import flwr as fl
import numpy as np
import pandas as pd
import torch

from ..config import DATA_DIR
from .model import AQI_SCALE, INPUT_LEN, AQIMLP, get_params, set_params

logger = logging.getLogger("vayusetu.fl.client")

LOCAL_EPOCHS = 2
BATCH_SIZE = 64
LR = 0.01
TRAIN_FRACTION = 0.8


def _build_windows(aqi: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    xs, ys = [], []
    for i in range(INPUT_LEN, len(aqi)):
        xs.append(aqi[i - INPUT_LEN:i])
        ys.append(aqi[i])
    return np.asarray(xs, dtype=np.float32), np.asarray(ys, dtype=np.float32)


class CityAQIClient(fl.client.NumPyClient):
    def __init__(self, city: str):
        self.city = city.strip().lower()
        # Only this client's own city data is loaded — enforced by path.
        df = pd.read_csv(DATA_DIR / f"historical_aqi_{self.city}.csv")
        aqi = df["aqi"].to_numpy(dtype=np.float32) / AQI_SCALE
        X, y = _build_windows(aqi)
        split = int(len(X) * TRAIN_FRACTION)
        self.X_train = torch.from_numpy(X[:split])
        self.y_train = torch.from_numpy(y[:split]).unsqueeze(1)
        self.X_val = torch.from_numpy(X[split:])
        self.y_val = torch.from_numpy(y[split:]).unsqueeze(1)
        self.model = AQIMLP()

    def get_parameters(self, config):
        return get_params(self.model)

    def fit(self, parameters, config):
        torch.manual_seed(42)  # fixed seed: reproducible demo runs
        set_params(self.model, parameters)
        optimizer = torch.optim.SGD(self.model.parameters(), lr=LR)
        loss_fn = torch.nn.MSELoss()
        self.model.train()
        n = len(self.X_train)
        for _ in range(LOCAL_EPOCHS):
            perm = torch.randperm(n)
            for i in range(0, n, BATCH_SIZE):
                idx = perm[i:i + BATCH_SIZE]
                optimizer.zero_grad()
                loss = loss_fn(self.model(self.X_train[idx]), self.y_train[idx])
                loss.backward()
                optimizer.step()
        val_loss = self._val_loss()
        # "city" travels in fit metrics so the aggregator can attribute losses
        # without relying on client ids.
        return get_params(self.model), n, {"loss": float(val_loss), "city": self.city}

    def evaluate(self, parameters, config):
        set_params(self.model, parameters)
        val_loss = self._val_loss()
        return float(val_loss), len(self.X_val), {"loss": float(val_loss), "city": self.city}

    def _val_loss(self) -> float:
        self.model.eval()
        with torch.no_grad():
            loss = torch.nn.functional.mse_loss(self.model(self.X_val), self.y_val)
        self.model.train()
        return float(loss)
