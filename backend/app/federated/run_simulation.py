"""Runs the federated simulation: the fixed city cohort (see app.cities) +
FedAvg server in ONE process using Flower's simulation API (no sockets/ports —
avoids "client can't connect to server" bugs entirely).

The cohort is deliberately smaller than the full city network: a simulation
scales linearly in clients, and the convergence chart can only carry a handful
of local loss lines.

Hardcoded 8 rounds for a predictable, short demo runtime. Writes round-by-round
progress to status.json via atomic writes so GET /api/federated/status can
serve live updates without ever reading a half-written file.

Run with:  python -m app.federated.run_simulation   (cwd = backend/)
"""
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vayusetu.fl.simulation")

NUM_ROUNDS = 8  # hardcoded on purpose — not configurable for the hackathon demo

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import FEDERATED_CITIES  # noqa: E402
from app.federated.client import CityAQIClient  # noqa: E402
from app.federated.server import STATUS_PATH, RecordingFedAvg, StatusRecorder, atomic_write_json  # noqa: E402

NUM_CLIENTS = len(FEDERATED_CITIES)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def client_fn(context):
    """flwr 1.11 passes a Context; the simulation puts the client index into
    node_config["partition-id"] (same value the legacy `cid` string carried)."""
    cid = None
    node_config = getattr(context, "node_config", None)
    if isinstance(node_config, dict):
        cid = node_config.get("partition-id")
    if cid is None:
        cid = getattr(context, "node_id", None)
    try:
        idx = int(cid)
    except (TypeError, ValueError):
        idx = 0
    # flwr 1.11 simulation requires a Client (not NumPyClient) — convert.
    return CityAQIClient(FEDERATED_CITIES[idx % NUM_CLIENTS]).to_client()


def main() -> None:
    recorder = StatusRecorder(STATUS_PATH)
    st = recorder.read()
    st.pop("error_message", None)  # never carry a stale error into a new run
    st.update({"status": "running", "rounds": [], "completed_at": None, "started_at": _now()})
    recorder.write(st)

    try:
        from flwr.server import ServerConfig
        from flwr.simulation import start_simulation

        try:
            import torch
            torch.manual_seed(42)  # fixed seed everywhere for reproducibility
        except Exception:
            pass

        strategy = RecordingFedAvg(
            recorder=recorder,
            fraction_fit=1.0,
            fraction_evaluate=0.0,  # server-side global eval is done in the recorder
            min_fit_clients=NUM_CLIENTS,
            min_available_clients=NUM_CLIENTS,
        )
        start_simulation(
            client_fn=client_fn,
            num_clients=NUM_CLIENTS,
            config=ServerConfig(num_rounds=NUM_ROUNDS),
            strategy=strategy,
            client_resources={"num_cpus": 1, "num_gpus": 0.0},
            ray_init_args={"include_dashboard": False, "ignore_reinit_error": True, "num_cpus": NUM_CLIENTS},
        )
        st = recorder.read()
        st["status"] = "completed"
        st["completed_at"] = _now()
        recorder.write(st)
        logger.info("federated simulation completed: %s rounds", len(st.get("rounds", [])))
    except Exception as exc:
        # Never leave the UI stuck on "running": mark completed with whatever
        # rounds were recorded, and surface the error message in the file.
        logger.error("federated simulation failed: %s", exc, exc_info=True)
        try:
            st = recorder.read()
            st["status"] = "completed"
            st["completed_at"] = _now()
            st["error_message"] = str(exc)
            recorder.write(st)
        except Exception:
            atomic_write_json(STATUS_PATH, {
                "status": "completed",
                "rounds": [],
                "started_at": None,
                "completed_at": _now(),
                "error_message": str(exc),
            })


if __name__ == "__main__":
    main()
