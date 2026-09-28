"""Error envelope + response sanitiser (section 11, section 12).

Every non-2xx response uses the envelope {"error": true, "message": str,
"details"?: any}. Every JSON response passes through the sanitiser, which
converts numpy scalar types to Python types and NaN/Inf to None before the
response leaves the process.
"""
import json
import logging
import math
from typing import Any

import numpy as np
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("vayusetu.errors")


def error_envelope(message: str, details: Any = None, status_code: int = 500) -> JSONResponse:
    content: dict[str, Any] = {"error": True, "message": message}
    if details is not None:
        content["details"] = sanitize(details)
    return JSONResponse(status_code=status_code, content=content)


def _is_bad_float(v: float) -> bool:
    return math.isnan(v) or math.isinf(v)


def sanitize(obj: Any) -> Any:
    """Recursively convert numpy types to Python types and NaN/Inf to None.

    Applied to every JSON payload so no response can ever contain NaN or
    Infinity tokens (illegal JSON) or numpy reprs.
    """
    if obj is None or isinstance(obj, (str, bool)):
        return obj
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        v = float(obj)
        return None if _is_bad_float(v) else v
    if isinstance(obj, float):
        return None if _is_bad_float(obj) else obj
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, dict):
        return {str(k): sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [sanitize(v) for v in obj]
    # pandas NaT and similar objects land here via str(); anything exotic is
    # stringified rather than crashing the serialiser.
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return str(obj)


class SanitizingJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return super().render(sanitize(content))


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError):
        # First error string only; the raw pydantic dump is noisy in the UI.
        try:
            first = exc.errors()[0]
            loc = ".".join(str(p) for p in first.get("loc", []) if p != "body")
            msg = first.get("msg", "invalid request")
            message = f"{loc}: {msg}" if loc else msg
        except Exception:
            message = "invalid request"
        return error_envelope(message, details=exc.errors(), status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def _http_handler(request: Request, exc: StarletteHTTPException):
        return error_envelope(str(exc.detail), status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def _catch_all(request: Request, exc: Exception):
        logger.exception("unhandled error on %s %s", request.method, request.url.path)
        return error_envelope("internal server error", status_code=500)
