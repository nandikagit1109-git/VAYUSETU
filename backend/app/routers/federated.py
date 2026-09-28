"""Federated endpoints (section 11.3)."""
import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..federated import runner
from ..store import DataStore

logger = logging.getLogger("vayusetu.federated")
router = APIRouter(prefix="/api/federated", tags=["federated"])


@router.get("/status")
def federated_status():
    return runner.read_status()


@router.post("/run")
def federated_run():
    store = DataStore.instance()
    started = runner.start_run_async(store, done_callback=_on_model_ready)
    if not started:
        return {"message": "already running"}
    return JSONResponse(status_code=202, content={"message": "started"})


def _on_model_ready(version: str) -> None:
    from ..services.forecast_service import set_model

    _, params = runner.load_global_model()
    set_model(version, params)


@router.get("/eval")
def federated_eval():
    from ..federated.evaluate import load_eval

    data = load_eval()
    if not data:
        return {"available": False, "rows": [], "mean_mae_persistence": None,
                "mean_mae_local": None, "mean_mae_federated": None}
    return data
