"""Shared GRU model (section 6). Same architecture and same initial weights
(seed 42) for every client and for the local-only baselines."""
import numpy as np
import torch
from torch import nn

INPUT_SIZE = 23
HIDDEN_SIZE = 32
NUM_LAYERS = 1
OUTPUT_SIZE = 3


def seed_everything(seed: int) -> None:
    import random

    random.seed(seed)
    try:
        import numpy as np

        np.random.seed(seed)
    except Exception:
        pass
    torch.manual_seed(seed)


def build_model(seed: int = 42) -> nn.Module:
    torch.manual_seed(seed)
    return nn.Sequential(
        GRUFeatureExtractor(INPUT_SIZE, HIDDEN_SIZE, NUM_LAYERS),
        nn.Linear(HIDDEN_SIZE, OUTPUT_SIZE),
    )


class GRUFeatureExtractor(nn.Module):
    def __init__(self, input_size: int, hidden_size: int, num_layers: int) -> None:
        super().__init__()
        self.gru = nn.GRU(
            input_size=input_size, hidden_size=hidden_size,
            num_layers=num_layers, batch_first=True,
        )
        self.hidden_size = hidden_size
        self.num_layers = num_layers

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, seq, features) -> last time step's hidden state.
        out, _ = self.gru(x)
        return out[:, -1, :]


def get_parameters(model: nn.Module) -> list:
    return [p.detach().clone().numpy().astype("float32") for p in model.state_dict().values()]


def set_parameters(model: nn.Module, params: list) -> None:
    state_dict = {}
    for (name, _), arr in zip(model.state_dict().items(), params):
        state_dict[name] = torch.tensor(np.asarray(arr), dtype=torch.float32)
    model.load_state_dict(state_dict)
