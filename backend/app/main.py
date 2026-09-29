"""FastAPI app entrypoint: lifespan startup (section 12), error envelope
handlers, sanitising JSON, and router includes.

Startup order: load config -> seed RNGs -> init DB -> build or load master
table -> tiering -> DataStore -> seed reports if empty -> load global model or
maybe start background FL -> yield. Everything except background training must
finish in under 15 seconds; the master table is loaded exactly once.
"""
import logging
import math
import random
from contextlib import asynccontextmanager

import numpy as np
import torch
from fastapi import FastAPI

from .config import AUTO_TRAIN_ON_START, SEED
from .db import get_session, init_db
from .errors import SanitizingJSONResponse, install_error_handlers
from .routers import aqi, alerts, cities, federated, forecast, hotspots, meta, reports
from .store import DataStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vayusetu")

DEFAULT_MODEL = {
    "version": None,
    "params": None,
}


def _seed_reports_if_empty() -> None:
    from datetime import datetime, timedelta, timezone

    from sqlmodel import func, select

    from .tables import CitizenReportRow

    with get_session() as session:
        count = session.exec(select(func.count()).select_from(CitizenReportRow)).one()
        if count and count > 0:
            return

        store = DataStore.instance()
        rng = random.Random(SEED)
        tier1 = [c for c in store.active_cities() if store.tier_of(c.city_id) == 1]
        rows = []
        for i in range(12):
            city = tier1[i % len(tier1)]
            # Position within 10 km of the city centre (0.09 deg lat ~ 10 km).
            dlat = rng.uniform(-0.09, 0.09)
            cos_lat = max(0.2, math.cos(math.radians(city.latitude)))
            dlon = rng.uniform(-0.09, 0.09) / cos_lat
            # Spread over the previous 20 hours; manual-style score near the
            # city's latest AQI, +/- 40 (section 10).
            created = datetime.now(timezone.utc) - timedelta(minutes=rng.randint(5, 20 * 60))
            ref = store.latest_aqi(city.city_id)[0]
            base = ref if ref is not None else 100.0
            score = round(min(480.0, max(20.0, base + rng.uniform(-40, 40))), 1)
            rows.append(CitizenReportRow(
                latitude=round(city.latitude + dlat, 4),
                longitude=round(city.longitude + dlon, 4),
                city_id=city.city_id,
                haze_score=score,
                confidence=0.4,
                trust_weight=round(min(1.0, max(0.2, 1.0 - abs(score - base) / 250.0)), 4),
                source="seed",
                photo_sha256=None,
                created_at=created,
            ))
        session.add_all(rows)
        session.commit()
        logger.info("seeded %d citizen reports", len(rows))


def _load_or_train_model() -> None:
    from .federated import runner
    from .services.forecast_service import set_model

    version, params = runner.load_global_model()
    if version and params is not None:
        set_model(version, params)
        logger.info("loaded global model %s", version)
        return
    if AUTO_TRAIN_ON_START:
        started = runner.start_run_async(DataStore.instance(), done_callback=_on_model_ready)
        logger.info("no global model found; background FL run %s",
                    "started" if started else "already running")


def _on_model_ready(version: str) -> None:
    from .federated import runner
    from .services.forecast_service import set_model

    _, params = runner.load_global_model()
    set_model(version, params)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. config is loaded at import; seed all RNGs deterministically.
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)

    # 2. DB
    init_db()

    # 3-5. master table, tiering, registry (DataStore singleton).
    store = DataStore.instance()
    logger.info("data mode=%s demo_now=%s active cities=%d (t1=%d t2=%d t3=%d)",
                store.data_mode, store.demo_now, len(store.active_ids),
                sum(1 for c in store.active_cities() if store.tier_of(c.city_id) == 1),
                sum(1 for c in store.active_cities() if store.tier_of(c.city_id) == 2),
                sum(1 for c in store.active_cities() if store.tier_of(c.city_id) == 3))

    # 6. seed reports
    try:
        _seed_reports_if_empty()
    except Exception as exc:
        logger.warning("report seeding failed (continuing): %s", exc)

    # 7. model
    try:
        _load_or_train_model()
    except Exception as exc:
        logger.warning("model startup skipped (%s); forecasts use persistence", exc)

    yield


app = FastAPI(
    title="VayuSetu API",
    version="2.0.0",
    lifespan=lifespan,
    default_response_class=SanitizingJSONResponse,
)
install_error_handlers(app)

app.include_router(meta.router)
app.include_router(aqi.router)
app.include_router(cities.router)
app.include_router(reports.router)
app.include_router(hotspots.router)
app.include_router(forecast.router)
app.include_router(alerts.router)
app.include_router(federated.router)


@app.get("/health")
def health():
    return {"ok": True}
