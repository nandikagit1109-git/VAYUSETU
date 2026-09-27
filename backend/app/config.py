"""Environment configuration with safe offline defaults.

Every "live" integration is OFF by default and gated behind an env var so the
demo runs perfectly with no internet and no API keys. Missing env vars never
crash the app.
"""
import os
from pathlib import Path

from .cities import CITY_TABLE, FEDERATED_CITIES

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_DIR / "data"
UPLOAD_DIR = BACKEND_DIR / "uploads"
DB_PATH = BACKEND_DIR / "vayusetu.db"

DATABASE_URL = os.getenv("VAYUSETU_DB_URL", f"sqlite:///{DB_PATH.as_posix()}")

# Optional stretch integrations — OFF by default.
ENABLE_TWILIO = os.getenv("ENABLE_TWILIO", "false").lower() == "true"
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")
ENABLE_LIVE_SATELLITE = os.getenv("ENABLE_LIVE_SATELLITE", "false").lower() == "true"

# Cities are defined once in app.cities; these are the derived lookups the rest
# of the backend uses (lowercase keys throughout).
CITIES: dict[str, tuple[float, float]] = {c["key"]: (c["lat"], c["lon"]) for c in CITY_TABLE}
