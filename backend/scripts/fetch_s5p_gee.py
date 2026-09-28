"""Optional stretch fetch script: Sentinel-5P via Google Earth Engine.

Run manually with internet and Earth Engine auth:
    earthengine authenticate && python scripts/fetch_s5p_gee.py

Writes backend/data/raw/s5p/{city_id}.csv with columns
date,no2,so2,co,aai. Units are converted to the master-table units:
NO2/SO2 in umol/m2, CO in mmol/m2 (molecules/m2 divided by 6.022e23 * 1e6 for
umol, * 1e3 for mmol), AAI dimensionless. Requires the `earthengine-api` and
`ee` packages plus an approved GEE account; this script is never run at app
startup and its absence never affects the offline demo.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.config import RAW_DIR  # noqa: E402
from app.data.registry import load_cities  # noqa: E402

AVOGADRO = 6.02214076e23


def main() -> None:
    try:
        import ee
    except ImportError:
        print("earthengine-api is not installed: pip install earthengine-api")
        sys.exit(1)
    try:
        ee.Initialize()
    except Exception as exc:
        print(f"Earth Engine initialisation failed ({exc}). Run: earthengine authenticate")
        sys.exit(1)

    end = date(2025, 11, 30)
    start = end - timedelta(days=90)
    collection = ee.ImageCollection("COPERNICUS/S5P/OFFL/L3_NO2")
    print("NOTE: this stretch script is a template; SO2/CO/AAI need their own "
          "collections (S5P/OFFL/L3_SO2, L3_CO, L3_AER_AI). NO2 is fetched as a "
          "worked example per city.")

    cities = load_cities()
    for c in cities:
        point = ee.Geometry.Point(c.longitude, c.latitude)
        coll = collection.filterDate(start.isoformat(), (end + timedelta(days=1)).isoformat()).select("tropospheric_NO2_column_number_density")
        means = coll.map(lambda img: img.set("date", img.date().format("YYYY-MM-dd"))).toList(coll.size())
        print(f"  {c.city_id}: fetching {start}..{end} (this can take a while)")
        try:
            rows = ["date,no2,so2,co,aai"]
            info = means.getInfo()
            for item in info:
                img = ee.Image(item)
                d = img.get("date").getInfo()
                val = img.reduceRegion(ee.Reducer.mean(), point, 5000).get("tropospheric_NO2_column_number_density").getInfo()
                if val is None:
                    continue
                umol = float(val) / AVOGADRO * 1e6
                rows.append(f"{d},{umol:.4f},,,")  # so2/co/aai need other collections
            out = RAW_DIR / "s5p" / f"{c.city_id}.csv"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text("\n".join(rows) + "\n", encoding="utf-8")
            print(f"    wrote {out} ({len(rows) - 1} days)")
        except Exception as exc:
            print(f"    FAILED {c.city_id}: {exc}")
    print("Done.")


if __name__ == "__main__":
    main()
