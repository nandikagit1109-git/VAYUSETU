"""Environment configuration with safe offline defaults (section 5.6).

Every constant is overridable by env var. The demo runs fully offline with
no API keys: DATA_MODE=synthetic is the default and real-data mode falls
back to synthetic on any missing file or schema mismatch.
"""
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
DB_PATH = BACKEND_DIR / "vayusetu.db"

DATABASE_URL = os.getenv("VAYUSETU_DB_URL", f"sqlite:///{DB_PATH.as_posix()}")


def _env_str(key: str, default: str) -> str:
    return os.getenv(key, default)


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        return default


def _env_bool(key: str, default: bool) -> bool:
    return os.getenv(key, str(default)).strip().lower() in ("1", "true", "yes")


def _env_float_list(key: str, default: str) -> list[float]:
    raw = os.getenv(key, default)
    try:
        return [float(x) for x in raw.split(",") if x.strip()]
    except ValueError:
        return [float(x) for x in default.split(",") if x.strip()]


# --- data mode (section 5.6) ---
DATA_MODE: str = _env_str("DATA_MODE", "synthetic").strip().lower()
if DATA_MODE not in ("synthetic", "real"):
    DATA_MODE = "synthetic"

FIRE_RADIUS_KM: float = _env_float("FIRE_RADIUS_KM", 500.0)
WINDOW_DAYS: int = _env_int("WINDOW_DAYS", 14)
HORIZONS: list[int] = [int(h) for h in _env_float_list("HORIZONS", "1,2,3")]
MIN_GROUND_DAYS: int = _env_int("MIN_GROUND_DAYS", 90)
MIN_AUX_DAYS: int = _env_int("MIN_AUX_DAYS", 30)
MIN_TRAIN_WINDOWS: int = _env_int("MIN_TRAIN_WINDOWS", 60)

FL_ROUNDS: int = _env_int("FL_ROUNDS", 8)
FL_LOCAL_EPOCHS: int = _env_int("FL_LOCAL_EPOCHS", 2)
FL_BATCH_SIZE: int = _env_int("FL_BATCH_SIZE", 64)
FL_LR: float = _env_float("FL_LR", 0.001)
FL_ENGINE: str = _env_str("FL_ENGINE", "builtin").strip().lower()
AUTO_TRAIN_ON_START: bool = _env_bool("AUTO_TRAIN_ON_START", True)
REBUILD_DATA: bool = _env_bool("REBUILD_DATA", False)

NEIGHBOR_RADIUS_KM: float = _env_float("NEIGHBOR_RADIUS_KM", 400.0)
REPORT_MAX_DISTANCE_KM: float = _env_float("REPORT_MAX_DISTANCE_KM", 200.0)
PHOTO_MAX_BYTES: int = _env_int("PHOTO_MAX_BYTES", 5_000_000)
SEED: int = _env_int("SEED", 42)
