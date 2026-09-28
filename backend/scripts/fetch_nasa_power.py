"""Optional fetch script: NASA POWER daily weather per registry city.

Run manually with internet: python scripts/fetch_nasa_power.py
Uses the keyless POWER daily point API. Writes backend/data/raw/power/{city_id}.csv
with columns: date,T2M,RH2M,PS,WS10M,WD10M (missing days carry -999 sentinels,
which the real loader converts to NaN). Prints exactly what it wrote.
"""
import sys
import time
from pathlib import Path

import requests

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.config import RAW_DIR  # noqa: E402
from app.data.registry import load_cities  # noqa: E402

URL = "https://power.larc.nasa.gov/api/temporal/daily/point"


def fetch_city(city_id: str, lat: float, lon: float) -> str:
    params = {
        "start": "20230101",
        "end": "20251130",
        "latitude": lat,
        "longitude": lon,
        "community": "AG",
        "parameters": "T2M,RH2M,PS,WS10M,WD10M",
        "format": "JSON",
    }
    r = requests.get(URL, params=params, timeout=60)
    r.raise_for_status()
    data = r.json()
    props = data["properties"]["parameter"]
    dates = sorted(props["T2M"].keys())
    lines = ["date,T2M,RH2M,PS,WS10M,WD10M"]
    for d in dates:
        lines.append(",".join(
            str(props[k].get(d, -999)) for k in ("T2M", "RH2M", "PS", "WS10M", "WD10M")
        ).replace("None", "-999"))
        lines[-1] = f"{d},{lines[-1]}"
    out = RAW_DIR / "power" / f"{city_id}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return f"{out} ({len(dates)} days)"


def main() -> None:
    cities = load_cities()
    print(f"Fetching NASA POWER daily weather for {len(cities)} cities...")
    for c in cities:
        try:
            wrote = fetch_city(c.city_id, c.latitude, c.longitude)
            print(f"  wrote {wrote}")
            time.sleep(0.5)  # be polite to the free API
        except Exception as exc:
            print(f"  FAILED {c.city_id}: {exc}")
    print("Done. Enable DATA_MODE=real to use these files.")


if __name__ == "__main__":
    main()
