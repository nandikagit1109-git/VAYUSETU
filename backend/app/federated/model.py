"""Shared small PyTorch model — identical architecture for all FL clients
(federated averaging requires this). Input: last 24 hourly AQI values
(normalised to 0-1). Output: next-hour AQI (normalised)."""
import numpy as np
import torch
import torch.nn as nn

INPUT_LEN = 24
AQI_SCALE = 500.0


class AQIMLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(INPUT_LEN, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
        )

    def forward(self, x):
        return self.net(x)


def get_params(model: nn.Module) -> list[np.ndarray]:
    return [v.detach().cpu().numpy().copy() for v in model.state_dict().values()]


def set_params(model: nn.Module, params: list[np.ndarray]) -> None:
    state = model.state_dict()
    new_state = {k: torch.tensor(np.array(v, copy=True)) for k, v in zip(state.keys(), params)}
    model.load_state_dict(new_state)
