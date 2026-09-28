"""FLClient (section 6): one participant city.

The client holds ONLY its own city's arrays. fit() returns parameters plus
scalars; evaluate() returns scalars. It never returns arrays of data — that is
the federated boundary.
"""
import numpy as np
import torch
from torch import nn

from .model import build_model, get_parameters, set_parameters


def _loss_fn(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    return nn.functional.mse_loss(pred, target)


class FLClient:
    def __init__(
        self,
        city_id: str,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        seed: int = 42,
        batch_size: int = 64,
        lr: float = 0.001,
        local_epochs: int = 2,
    ) -> None:
        self.city_id = city_id
        self.X_train = X_train.astype(np.float32)
        self.y_train = y_train.astype(np.float32)
        self.X_val = X_val.astype(np.float32)
        self.y_val = y_val.astype(np.float32)
        self.seed = seed
        self.batch_size = batch_size
        self.lr = lr
        self.local_epochs = local_epochs
        # Every client starts from the same seeded architecture and weights.
        self.model = build_model(seed)
        self._g = torch.Generator().manual_seed(seed)

    def n_train(self) -> int:
        return int(self.X_train.shape[0])

    def n_val(self) -> int:
        return int(self.X_val.shape[0])

    def fit(self, global_params: list | None = None) -> tuple[list, int, float]:
        """Train FL_LOCAL_EPOCHS epochs from the given global parameters.

        Returns (params_as_list_of_numpy_float32, n_train,
        mean_train_loss_last_epoch).
        """
        if global_params is not None:
            set_parameters(self.model, global_params)
        self.model.train()
        opt = torch.optim.Adam(self.model.parameters(), lr=self.lr)

        n = self.X_train.shape[0]
        last_epoch_losses: list[float] = []
        for _epoch in range(self.local_epochs):
            order = torch.randperm(n, generator=self._g)
            epoch_losses = []
            for start in range(0, n, self.batch_size):
                idx = order[start:start + self.batch_size]
                xb = torch.from_numpy(self.X_train[idx.numpy()])
                yb = torch.from_numpy(self.y_train[idx.numpy()])
                opt.zero_grad()
                loss = _loss_fn(self.model(xb), yb)
                loss.backward()
                opt.step()
                epoch_losses.append(float(loss.detach()))
            last_epoch_losses = epoch_losses

        mean_loss = float(np.mean(last_epoch_losses)) if last_epoch_losses else 0.0
        return get_parameters(self.model), self.n_train(), mean_loss

    @torch.no_grad()
    def evaluate(self, global_params: list) -> tuple[float, list[float], int]:
        """Returns (val_mse_scaled, mae_aqi_per_horizon, n_val).

        mae_aqi_per_horizon is MAE * 500 (back in AQI units) per horizon.
        """
        set_parameters(self.model, global_params)
        self.model.eval()
        xb = torch.from_numpy(self.X_val)
        yb = torch.from_numpy(self.y_val)
        pred = self.model(xb)
        mse = float(nn.functional.mse_loss(pred, yb))
        mae = (pred - yb).abs().mean(dim=0) * 500.0
        return mse, [float(v) for v in mae], self.n_val()
