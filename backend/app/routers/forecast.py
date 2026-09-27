"""Forecast endpoints."""
import logging

from fastapi import APIRouter
from sqlmodel import col, delete, select

from ..db import get_session
from ..models import ForecastPoint
from ..services import forecast_model

logger = logging.getLogger("vayusetu.forecast")
router = APIRouter(prefix="/api/forecast", tags=["forecast"])


@router.get("")
def get_forecast(city: str):
    # Polled endpoint: on any internal problem return HTTP 200 with error:true
    # so the UI shows a "pending" state instead of breaking.
    try:
        fc = forecast_model.get_forecast(city)
    except forecast_model.ForecastUnavailable as exc:
        return {"error": True, "message": str(exc)}
    except Exception as exc:
        logger.warning("forecast failed for %s: %s", city, exc)
        return {"error": True, "message": f"forecast pending for {city}"}

    try:
        with get_session() as session:
            session.exec(delete(ForecastPoint).where(col(ForecastPoint.city) == fc["city"]))
            for p in fc["raw_points"]:
                session.add(ForecastPoint(
                    city=fc["city"],
                    forecast_for=p["forecast_for"],
                    predicted_aqi=p["predicted_aqi"],
                    lower_bound=p["lower_bound"],
                    upper_bound=p["upper_bound"],
                    generated_at=fc["generated_at"],
                ))
            session.commit()
    except Exception as exc:
        logger.warning("could not persist forecast points for %s: %s", fc["city"], exc)

    return {"city": fc["city"], "points": fc["points"]}
