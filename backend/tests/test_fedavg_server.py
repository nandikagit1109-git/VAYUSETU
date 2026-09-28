"""FedAvg server tests (section 14.5): toy weighted average + import guard."""
import ast
from pathlib import Path

import numpy as np

from app.federated.server import weighted_average


def test_weighted_average_toy_example():
    # Two "layers": a bias (1 vector) and a weight (2 vector).
    p1 = [np.array([2.0], dtype=np.float32), np.array([4.0, 6.0], dtype=np.float32)]
    p2 = [np.array([4.0], dtype=np.float32), np.array([0.0, 0.0], dtype=np.float32)]
    # n1=3, n2=1 -> weights 0.75 / 0.25.
    avg = weighted_average([p1, p2], [3, 1])
    assert np.allclose(avg[0], [2.5], atol=1e-6)  # 0.75*2 + 0.25*4
    assert np.allclose(avg[1], [3.0, 4.5], atol=1e-6)  # 0.75*[4,6] + 0.25*[0,0]


def test_weighted_average_single_client_is_identity():
    p = [np.array([7.0], dtype=np.float32)]
    avg = weighted_average([p], [5])
    assert np.allclose(avg[0], [7.0], atol=1e-7)


def test_weighted_average_output_dtype_float32():
    p1 = [np.array([1.0, 2.0], dtype=np.float64)]
    p2 = [np.array([3.0, 4.0], dtype=np.float64)]
    avg = weighted_average([p1, p2], [1, 1])
    assert avg[0].dtype == np.float32


def test_server_module_does_not_import_data_or_store():
    """Trap guard: server.py must never import app.data or app.store."""
    server_path = Path(__file__).resolve().parents[1] / "app" / "federated" / "server.py"
    tree = ast.parse(server_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith(("app.data", "app.store")), alias.name
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            assert not mod.startswith(("app.data", "app.store", "data", "store")), mod
