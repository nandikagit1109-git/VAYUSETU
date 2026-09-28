"""Forecast endpoint (section 11.3).

Expected "not available" states return HTTP 200 with the error envelope so the
UI can render a pending/empty state; unknown cities are 404 envelopes.
"""
import logging

from fastapi import APIRouter, Query

from ..errors import error_envelope, sanitize
from ..services.forecast_service import ForecastUnavailable, get_forecast
from ..store import DataStore

logger = logging.getLogger("vayusetu.forecast")
router = APIRouter(prefix="/api/forecast", tags=["forecast"])


@router.get("")
def get_city_forecast(city_id: str = Query(...)):
    store = DataStore.instance()
    if store.city(city_id) is None:
        return error_envelope(f"unknown city {city_id}", status_code=404)
    try:
        fc = get_forecast(store, city_id)
    except ForecastUnavailable as exc:
        # Polled endpoint: expected unavailability is a 200 envelope.
        return {"error": True, "message": str(exc)}
    except Exception as exc:
        logger.warning("forecast failed for %s: %s", city_id, exc)
        return {"error": True, "message": f"forecast pending for {city_id}"}
    return sanitize(fc)
