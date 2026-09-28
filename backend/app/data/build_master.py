"""Master table file I/O (section 5.2).

Produces data/processed/master_daily.csv (city_id + date keyed) and
data/processed/fires_daily.csv. Column order is fixed by
synthetic.MASTER_COLUMNS; missing values are empty cells, never 0 or -999.
"""
import logging
from pathlib import Path

import pandas as pd

from ..config import PROCESSED_DIR, REBUILD_DATA
from .synthetic import MASTER_COLUMNS

logger = logging.getLogger("vayusetu.build_master")

MASTER_PATH = PROCESSED_DIR / "master_daily.csv"
FIRES_PATH = PROCESSED_DIR / "fires_daily.csv"


def needs_rebuild() -> bool:
    return REBUILD_DATA or not MASTER_PATH.exists()


def write_processed(master: pd.DataFrame, fires: pd.DataFrame | None) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    cols = [c for c in MASTER_COLUMNS if c in master.columns]
    master[cols].to_csv(MASTER_PATH, index=False)
    if fires is not None:
        fires.to_csv(FIRES_PATH, index=False)
        logger.info("wrote %s (%d fire points)", FIRES_PATH.name, len(fires))


def load_master() -> pd.DataFrame:
    df = pd.read_csv(MASTER_PATH, dtype={"city_id": str})
    df["date"] = df["date"].astype(str)
    return df


def load_fires() -> pd.DataFrame | None:
    if not FIRES_PATH.exists():
        return None
    try:
        return pd.read_csv(FIRES_PATH, dtype={"date": str})
    except Exception as exc:
        logger.warning("fires_daily.csv unreadable (%s); fire features disabled", exc)
        return None
