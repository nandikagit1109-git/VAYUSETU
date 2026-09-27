"""FastAPI app entrypoint: CORS, router includes, startup seeding."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import get_session, init_db
from .routers import alerts, federated, forecast, hotspots, reports
from .services import mock_data, seed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vayusetu")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    try:
        mock_data.preload()
    except Exception as exc:  # startup must never crash on mock data issues
        logger.warning("mock data preload failed (falling back): %s", exc)
    try:
        with get_session() as session:
            seed.seed_all(session)
    except Exception as exc:
        logger.warning("seeding failed (continuing): %s", exc)
    yield


app = FastAPI(title="VayuSetu API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reports.router)
app.include_router(hotspots.router)
app.include_router(forecast.router)
app.include_router(alerts.router)
app.include_router(federated.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
