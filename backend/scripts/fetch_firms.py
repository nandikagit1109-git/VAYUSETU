"""Optional fetch script: NASA FIRMS active fire points.

Run manually with internet and a MAP_KEY: FIRMS_MAP_KEY=... python scripts/fetch_firms.py
Reads FIRMS_MAP_KEY from the environment and exits with a clear message when it
is absent. Writes backend/data/raw/firms/firms_<window>.csv with columns
latitude,longitude,acq_date,frp (confidence included when returned).
"""
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import requests

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.config import RAW_DIR  # noqa: E402

URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/VIIRS_NOAA20_NRT/{area}/{days}"


def main() -> None:
    key = os.getenv("FIRMS_MAP_KEY", "").strip()
    if not key:
        print("FIRMS_MAP_KEY is not set. Get a free MAP_KEY at "
              "https://firms.modaps.eosdis.nasa.gov/api/map_key/ and run:")
        print("  FIRMS_MAP_KEY=your_key python scripts/fetch_firms.py")
        sys.exit(1)

    days = os.getenv("FIRMS_DAYS", "10")
    # India bbox: south, west, north, east (lat_min, lon_min, lat_max, lon_max).
    area = "6.0,68.0,37.5,97.5"
    url = URL.format(key=key, area=area, days=days)
    print(f"Fetching FIRMS VIIRS fire points for {days} days over India...")
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    text = r.text
    if text.lstrip().startswith("Invalid"):
        print(f"FIRMS rejected the request: {text.strip()[:200]}")
        sys.exit(1)

    out = RAW_DIR / "firms" / f"firms_{date.today().isoformat()}_{days}d.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    n_rows = max(0, len(text.strip().splitlines()) - 1)
    print(f"wrote {out} ({n_rows} fire points, columns latitude,longitude,acq_date,frp)")
    print("Done. Enable DATA_MODE=real to use these files.")


if __name__ == "__main__":
    main()
