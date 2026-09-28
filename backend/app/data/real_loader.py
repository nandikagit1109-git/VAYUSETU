"""Real-data mode loaders (section 5.5), enabled with DATA_MODE=real.

Inputs are user-supplied files under backend/data/raw/. Any missing file or
schema mismatch raises RawDataError, which the caller turns into a synthetic
fallback plus a `fallback_reason` reported in /api/meta. Cities are always
discovered from the file contents — never assumed.
"""
import logging
import math
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import FIRE_RADIUS_KM, RAW_DIR
from ..geo import haversine_km
from .synthetic import MASTER_COLUMNS

logger = logging.getLogger("vayusetu.real_loader")

CPCB_REQUIRED = {"City", "Date", "PM2.5", "PM10", "AQI"}
POWER_REQUIRED = {"date", "T2M", "RH2M", "PS", "WS10M", "WD10M"}
FIRMS_REQUIRED = {"latitude", "longitude", "acq_date", "frp"}
S5P_REQUIRED = {"date", "no2", "so2", "co", "aai"}

INDIA_BBOX = (6.5, 37.5, 68.0, 97.5)  # lat_min, lat_max, lon_min, lon_max


class RawDataError(Exception):
    pass


def _require_columns(df: pd.DataFrame, required: set[str], label: str) -> None:
    missing = required - set(df.columns)
    if missing:
        raise RawDataError(f"{label} missing columns: {sorted(missing)}")


def _norm_name(name: str) -> str:
    return name.strip().lower()


def load_cpcb(cities: list) -> tuple[pd.DataFrame, list[str]]:
    """Returns (cpcb_frame, unknown_city_names). Raises RawDataError on failure."""
    path = RAW_DIR / "cpcb" / "city_day.csv"
    if not path.exists():
        raise RawDataError(f"missing file: raw/cpcb/city_day.csv")
    try:
        df = pd.read_csv(path)
    except Exception as exc:
        raise RawDataError(f"could not read raw/cpcb/city_day.csv: {exc}") from exc
    _require_columns(df, CPCB_REQUIRED, "raw/cpcb/city_day.csv")

    registry = {c.city_id: c for c in cities}
    by_name = {_norm_name(c.name): c for c in cities}
    by_id = {_norm_name(c.city_id): c for c in cities}

    df["_key"] = df["City"].astype(str).map(_norm_name)
    known = []
    unknown = sorted(set(df["_key"]) - set(by_name) - set(by_id))
    for key, group in df.groupby("_key"):
        city = by_name.get(key) or by_id.get(key)
        if city is None:
            continue  # skipped with warning by caller
        known.append((city, group))

    frames = []
    for city, group in known:
        g = group.rename(columns={
            "Date": "date", "PM2.5": "pm25", "PM10": "pm10", "NO2": "no2",
            "SO2": "so2", "CO": "co", "O3": "o3", "AQI": "aqi",
        })
        out = pd.DataFrame({
            "city_id": city.city_id,
            "date": pd.to_datetime(g["date"]).dt.strftime("%Y-%m-%d"),
            "pm25": pd.to_numeric(g["pm25"], errors="coerce"),
            "pm10": pd.to_numeric(g["pm10"], errors="coerce"),
            "no2": pd.to_numeric(g["no2"], errors="coerce"),
            "so2": pd.to_numeric(g["so2"], errors="coerce"),
            "co": pd.to_numeric(g["co"], errors="coerce"),
            "o3": pd.to_numeric(g["o3"], errors="coerce"),
            "aqi": pd.to_numeric(g["aqi"], errors="coerce"),
        })
        frames.append(out)
    if not frames:
        raise RawDataError("raw/cpcb/city_day.csv contains no registry cities")
    merged = pd.concat(frames, ignore_index=True)
    for col in ("temp", "humidity", "pressure", "wind_speed", "wind_dir", "fire_count", "fire_frp",
                "s5p_no2_umol_m2", "s5p_so2_umol_m2", "s5p_co_mmol_m2", "aerosol_index"):
        merged[col] = np.nan
    return merged, unknown


def load_power(cities: list) -> pd.DataFrame | None:
    frames = []
    for c in cities:
        path = RAW_DIR / "power" / f"{c.city_id}.csv"
        if not path.exists():
            continue
        try:
            df = pd.read_csv(path)
        except Exception as exc:
            logger.warning("could not read %s (%s); city %s gets no weather", path, exc, c.city_id)
            continue
        _require_columns(df, POWER_REQUIRED, f"raw/power/{c.city_id}.csv")
        df = df.replace(-999, np.nan)
        frames.append(pd.DataFrame({
            "city_id": c.city_id,
            "date": pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d"),
            "temp": pd.to_numeric(df["T2M"], errors="coerce"),
            "humidity": pd.to_numeric(df["RH2M"], errors="coerce"),
            "pressure": pd.to_numeric(df["PS"], errors="coerce"),  # already kPa
            "wind_speed": pd.to_numeric(df["WS10M"], errors="coerce"),
            "wind_dir": pd.to_numeric(df["WD10M"], errors="coerce"),
        }))
    if not frames:
        return None
    return pd.concat(frames, ignore_index=True)


def load_firms() -> pd.DataFrame | None:
    """Concatenated, deduped fire points clipped to the India bbox."""
    firms_dir = RAW_DIR / "firms"
    if not firms_dir.exists():
        return None
    files = sorted(firms_dir.glob("*.csv"))
    if not files:
        return None
    frames = []
    for path in files:
        try:
            df = pd.read_csv(path)
        except Exception as exc:
            logger.warning("could not read %s (%s); skipped", path, exc)
            continue
        missing = FIRMS_REQUIRED - set(df.columns)
        if missing:
            logger.warning("%s missing columns %s; skipped", path, sorted(missing))
            continue
        frames.append(df[["latitude", "longitude", "acq_date", "frp"]])
    if not frames:
        return None
    all_points = pd.concat(frames, ignore_index=True)
    lat_min, lat_max, lon_min, lon_max = INDIA_BBOX
    inside = all_points[
        (all_points["latitude"].between(lat_min, lat_max))
        & (all_points["longitude"].between(lon_min, lon_max))
    ]
    inside = inside.drop_duplicates(subset=["latitude", "longitude", "acq_date", "frp"])
    out = pd.DataFrame({
        "date": pd.to_datetime(inside["acq_date"]).dt.strftime("%Y-%m-%d"),
        "latitude": inside["latitude"].astype(float),
        "longitude": inside["longitude"].astype(float),
        "frp": inside["frp"].astype(float),
        "source": "firms",
    })
    return out


def load_s5p(cities: list) -> pd.DataFrame | None:
    frames = []
    for c in cities:
        path = RAW_DIR / "s5p" / f"{c.city_id}.csv"
        if not path.exists():
            continue
        try:
            df = pd.read_csv(path)
        except Exception as exc:
            logger.warning("could not read %s (%s); city %s gets no satellite data", path, exc, c.city_id)
            continue
        missing = S5P_REQUIRED - set(df.columns)
        if missing:
            logger.warning("%s missing columns %s; skipped", path, sorted(missing))
            continue
        # Units: the fetch script documents the conversion to master units
        # (umol/m2 for NO2/SO2, mmol/m2 for CO, dimensionless AAI).
        frames.append(pd.DataFrame({
            "city_id": c.city_id,
            "date": pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d"),
            "s5p_no2_umol_m2": pd.to_numeric(df["no2"], errors="coerce"),
            "s5p_so2_umol_m2": pd.to_numeric(df["so2"], errors="coerce"),
            "s5p_co_mmol_m2": pd.to_numeric(df["co"], errors="coerce"),
            "aerosol_index": pd.to_numeric(df["aai"], errors="coerce"),
        }))
    if not frames:
        return None
    return pd.concat(frames, ignore_index=True)


def _fire_features(fires: pd.DataFrame, cities: list) -> pd.DataFrame:
    """Per-city fire_count/fire_frp within FIRE_RADIUS_KM, vectorized."""
    rows = []
    fire_by_date = {d: g for d, g in fires.groupby("date")}
    for c in cities:
        for d, g in fire_by_date.items():
            lats = g["latitude"].to_numpy(dtype=float)
            lons = g["longitude"].to_numpy(dtype=float)
            p1, l1 = math.radians(c.latitude), math.radians(c.longitude)
            p2, l2 = np.radians(lats), np.radians(lons)
            a = (np.sin((p2 - p1) / 2) ** 2
                 + math.cos(p1) * np.cos(p2) * np.sin((l2 - l1) / 2) ** 2)
            dist = 2 * 6371.0088 * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))
            sel = g[dist <= FIRE_RADIUS_KM]
            rows.append((c.city_id, d, len(sel), float(sel["frp"].sum()) if len(sel) else 0.0))
    return pd.DataFrame(rows, columns=["city_id", "date", "fire_count", "fire_frp"])


def build_real_frames(cities: list) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    """Assemble the master frame from raw files. Raises RawDataError when a
    required file is missing/invalid (caller falls back to synthetic)."""
    cpcb, unknown = load_cpcb(cities)
    if unknown:
        logger.warning("CPCB file contains %d cities not in the registry (skipped): %s",
                       len(unknown), ", ".join(unknown[:20]))

    master = cpcb.copy()
    power = load_power(cities)
    if power is not None:
        master = master.drop(columns=[c for c in ("temp", "humidity", "pressure", "wind_speed", "wind_dir") if c in master.columns])
        master = master.merge(power, on=["city_id", "date"], how="left")

    fires = load_firms()
    if fires is not None and len(fires):
        feats = _fire_features(fires, cities)
        master = master.drop(columns=[c for c in ("fire_count", "fire_frp") if c in master.columns])
        master = master.merge(feats, on=["city_id", "date"], how="left")
    else:
        logger.info("fire data not loaded: no FIRMS files under raw/firms/")

    s5p = load_s5p(cities)
    if s5p is not None:
        master = master.drop(columns=[c for c in ("s5p_no2_umol_m2", "s5p_so2_umol_m2", "s5p_co_mmol_m2", "aerosol_index") if c in master.columns])
        master = master.merge(s5p, on=["city_id", "date"], how="left")

    master = master[[c for c in MASTER_COLUMNS if c in master.columns]]
    return master, fires
