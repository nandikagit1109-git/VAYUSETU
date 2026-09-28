"""FedAvg server (section 6).

PRIVACY — exactly what crosses the city boundary in this system:
  1. Model parameter arrays (float32 numpy, the shared GRU weights).
  2. Per-client sample counts (n_train integers) used as aggregation weights.
  3. Scalar losses/metrics (train loss, validation MSE, MAE).
Nothing else leaves a city: no raw measurements, no windows, no per-row data.
This module intentionally imports nothing from app.data or app.store; it is
pure aggregation maths over parameter arrays.
"""
import numpy as np


def weighted_average(params_list: list, n_train_list: list[int]) -> list:
    """Sample-weighted FedAvg: sum_i (n_i / total_n) * params_i.

    All arrays are averaged as float32 consistently (trap 7: dtype mismatch).
    """
    if not params_list:
        raise ValueError("no client parameters to aggregate")
    if len(params_list) != len(n_train_list):
        raise ValueError("params and n_train lists must have the same length")
    total = float(sum(n_train_list))
    if total <= 0:
        raise ValueError("total training samples must be positive")

    avg: list[np.ndarray] = []
    for layer_idx in range(len(params_list[0])):
        acc = None
        for params, n in zip(params_list, n_train_list):
            arr = np.asarray(params[layer_idx], dtype=np.float32)
            contribution = arr * (float(n) / total)
            acc = contribution if acc is None else acc + contribution
        avg.append(np.asarray(acc, dtype=np.float32))
    return avg


def aggregate_round_results(client_results: list[tuple[str, list, int, float]]) -> tuple[list, dict[str, float]]:
    """Aggregate one round of fit() results.

    client_results: list of (city_id, params, n_train, train_loss).
    Returns (new_global_params, client_losses keyed by city_id).
    """
    params_list = [r[1] for r in client_results]
    n_train_list = [r[2] for r in client_results]
    losses = {r[0]: float(r[3]) for r in client_results}
    return weighted_average(params_list, n_train_list), losses
