"""Federated learning status/trigger endpoints.

The training itself runs in a separate subprocess (app/federated/run_simulation.py)
which writes round-by-round progress to status.json using atomic
write-temp-then-rename, so this router never reads a half-written file.
"""
import json
import logging
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..config import BACKEND_DIR

logger = logging.getLogger("vayusetu.federated")
router = APIRouter(prefix="/api/federated", tags=["federated"])

STATUS_PATH = Path(__file__).resolve().parents[1] / "federated" / "status.json"
STALE_AFTER = timedelta(minutes=5)


def _default_status() -> dict:
    return {"status": "idle", "rounds": [], "started_at": None, "completed_at": None}


def read_status() -> dict:
    try:
        with open(STATUS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        status = data.get("status")
        if status not in ("idle", "running", "completed"):
            return _default_status()
        rounds = [
            {
                "round": int(r["round"]),
                "client_losses": {
                    "delhi": float(r.get("client_losses", {}).get("delhi", 0.0)),
                    "kanpur": float(r.get("client_losses", {}).get("kanpur", 0.0)),
                    "pune": float(r.get("client_losses", {}).get("pune", 0.0)),
                },
                "global_loss": float(r.get("global_loss", 0.0)),
            }
            for r in data.get("rounds", [])
        ]
        return {
            "status": status,
            "rounds": rounds,
            "started_at": data.get("started_at"),
            "completed_at": data.get("completed_at"),
        }
    except FileNotFoundError:
        return _default_status()
    except Exception as exc:  # corrupt/partial file: never break the UI
        logger.warning("could not read federated status: %s", exc)
        return _default_status()


def write_status_atomic(payload: dict) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATUS_PATH.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    tmp.replace(STATUS_PATH)


def _is_stale(status: dict) -> bool:
    started = status.get("started_at")
    if not started:
        return True
    try:
        started_dt = datetime.fromisoformat(started)
        if started_dt.tzinfo is None:
            started_dt = started_dt.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - started_dt > STALE_AFTER
    except Exception:
        return True


@router.get("/status")
def get_status():
    return read_status()


@router.post("/run")
def run_federated():
    status = read_status()
    if status["status"] == "running" and not _is_stale(status):
        return {"message": "already running"}  # idempotent, never an error

    write_status_atomic({
        "status": "running",
        "rounds": [],
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
    })

    try:
        kwargs: dict = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL, "cwd": str(BACKEND_DIR)}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        subprocess.Popen([sys.executable, "-m", "app.federated.run_simulation"], **kwargs)
    except Exception as exc:
        logger.error("failed to spawn federated simulation: %s", exc)
        write_status_atomic(_default_status())
        return JSONResponse(status_code=500, content={"error": True, "message": f"could not start simulation: {exc}"})

    return JSONResponse(status_code=202, content={"message": "started"})
