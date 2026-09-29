"""GET /api/aqi (section 7b): point AQI for any lat/lon in India.

A query, not a submission: outside the India bounding box is an expected
"not available" state, returned as HTTP 200 with the error envelope — never a
hard 4xx/5xx for a valid coordinate.
"""
from fastapi import APIRouter, Query

from ..errors import error_envelope, sanitize
from ..services.point_aqi_service import estimate_point_aqi, outside_india
from ..store import DataStore

router = APIRouter(prefix="/api/aqi", tags=["aqi"])


@router.get("")
def point_aqi(
    latitude: float = Query(...),
    longitude: float = Query(...),
):
    if outside_india(latitude, longitude):
        return error_envelope("outside India", status_code=200)
    store = DataStore.instance()
    try:
        result = estimate_point_aqi(store, latitude, longitude)
    except LookupError as exc:
        return error_envelope(str(exc), status_code=200)
    except Exception:
        # Polled endpoint: never a stack trace; generic pending message.
        return error_envelope("point estimate unavailable", status_code=200)
    return sanitize(result)
