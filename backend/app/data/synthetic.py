"""Deterministic synthetic data generator (section 5.4).

A pure function of the seed: same seed in, byte-identical master table out.
Period 2023-12-01 .. 2025-11-30, DEMO_NOW = 2025-11-30. Randomness uses local
numpy Generator instances seeded from SEED so the output never depends on call
order or on other modules consuming the global numpy RNG.
"""
import math
import zlib
from datetime import date, timedelta

import numpy as np
import pandas as pd

from ..config import FIRE_RADIUS_KM, SEED

EARTH_R = 6371.0088

START_DATE = date(2023, 12, 1)
END_DATE = date(2025, 11, 30)
DEMO_NOW = END_DATE

# Stubble source point and distance bands (section 5.4).
STUBBLE_LAT, STUBBLE_LON = 30.4, 75.8
STUBBLE_BANDS = [(350.0, 1.1, 1), (900.0, 0.5, 2)]  # (max_km, coeff, lag); beyond -> (0.05, 3)
FAR_COEFF, FAR_LAG = 0.05, 3

# Fire boxes.
PH_BOX = (29.5, 31.8, 74.0, 77.2)  # Punjab/Haryana: lat_min, lat_max, lon_min, lon_max
CI_BOX = (19.0, 24.0, 78.0, 84.0)  # central-India background
HOTSPOT_PH_BOX = (29.0, 32.5, 73.5, 77.8)  # used by hotspot_service cause labelling

MASTER_COLUMNS = [
    "city_id", "date",
    "pm25", "pm10", "no2", "so2", "co", "o3", "aqi",
    "temp", "humidity", "pressure", "wind_speed", "wind_dir",
    "fire_count", "fire_frp",
    "s5p_no2_umol_m2", "s5p_so2_umol_m2", "s5p_co_mmol_m2", "aerosol_index",
]


def seasonal_multiplier(doy: int) -> float:
    return 1 + 0.5 * math.cos(2 * math.pi * (doy - 355) / 365) - 0.25 * math.exp(-(((doy - 210) / 35) ** 2))


def weekly_factor(dow: int) -> float:
    return 1 + 0.05 * math.sin(2 * math.pi * dow / 7)


def fire_intensity(doy: int) -> float:
    return math.exp(-(((doy - 305) / 12) ** 2)) + 0.3 * math.exp(-(((doy - 120) / 10) ** 2))


def stubble_contribution(R: float, dist_km: float, r_lagged: list[float]) -> float:
    """Stubble PM2.5 contribution for a city at distance dist_km.

    r_lagged[h - 1] must hold R(d - h) for h = 1..3 (the needed lags).
    """
    f_R = 250.0 * (1.0 - math.exp(-R / 120.0))
    if dist_km <= STUBBLE_BANDS[0][0]:
        coeff, lag = STUBBLE_BANDS[0][1], STUBBLE_BANDS[0][2]
    elif dist_km <= STUBBLE_BANDS[1][0]:
        coeff, lag = STUBBLE_BANDS[1][1], STUBBLE_BANDS[1][2]
    else:
        coeff, lag = FAR_COEFF, FAR_LAG
    return coeff * 250.0 * (1.0 - math.exp(-r_lagged[lag - 1] / 120.0))


def generate_fires() -> pd.DataFrame:
    """All synthetic fire points: date,latitude,longitude,frp,source."""
    n_days = (END_DATE - START_DATE).days + 1
    dates = [START_DATE + timedelta(days=i) for i in range(n_days)]
    rng = np.random.default_rng(SEED + 1)

    rows: list[tuple] = []
    for d in dates:
        doy = d.timetuple().tm_yday
        year_scale = 1.25 if d.year == 2025 else 1.0
        n_ph = rng.poisson(1 + 60 * fire_intensity(doy) * year_scale)
        n_ci = rng.poisson(2 + 15 * math.exp(-(((doy - 90) / 15) ** 2)))
        lat_min, lat_max, lon_min, lon_max = PH_BOX
        for _ in range(n_ph):
            lat = rng.uniform(lat_min, lat_max)
            lon = rng.uniform(lon_min, lon_max)
            frp = rng.lognormal(mean=math.log(20.0), sigma=0.6)
            rows.append((d.isoformat(), round(float(lat), 4), round(float(lon), 4), float(frp), "synthetic"))
        lat_min, lat_max, lon_min, lon_max = CI_BOX
        for _ in range(n_ci):
            lat = rng.uniform(lat_min, lat_max)
            lon = rng.uniform(lon_min, lon_max)
            frp = rng.lognormal(mean=math.log(20.0), sigma=0.6)
            rows.append((d.isoformat(), round(float(lat), 4), round(float(lon), 4), float(frp), "synthetic"))
    return pd.DataFrame(rows, columns=["date", "latitude", "longitude", "frp", "source"])


def _wind_dir_for(city_lat: float, month: int, rng) -> float:
    """Northwestern cities get northwesterly (315 deg) winds Oct-Feb; the rest
    get southwest monsoon-like winds. wind_dir is the direction FROM."""
    if city_lat > 24 and (10 <= month <= 12 or 1 <= month <= 2):
        return float(rng.normal(315.0, 35.0)) % 360.0
    return float(rng.normal(225.0, 60.0)) % 360.0


def _haversine_vec(lat1: float, lon1: float, lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
    """Vectorized haversine from one point to arrays of points (km)."""
    p1 = math.radians(lat1)
    l1 = math.radians(lon1)
    p2 = np.radians(np.asarray(lats, dtype=float))
    l2 = np.radians(np.asarray(lons, dtype=float))
    dp = p2 - p1
    dl = l2 - l1
    a = np.sin(dp / 2) ** 2 + math.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * EARTH_R * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def generate(cities: list) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (master_df, fires_df).

    cities: registry CityEntry list. Roles: ground -> all columns; aux_only ->
    weather+fire+satellite only; none -> no rows; skip -> not generated.
    """
    n_days = (END_DATE - START_DATE).days + 1
    dates = [START_DATE + timedelta(days=i) for i in range(n_days)]
    doys = np.array([d.timetuple().tm_yday for d in dates])
    dows = np.array([d.weekday() for d in dates])
    months = np.array([d.month for d in dates])

    fires_df = generate_fires()
    fire_dates = sorted(fires_df["date"].unique())

    # Pre-compute per-day stubble source strength R(d) from the Punjab/Haryana points.
    ph_mask = (
        (fires_df["latitude"] >= PH_BOX[0]) & (fires_df["latitude"] <= PH_BOX[1])
        & (fires_df["longitude"] >= PH_BOX[2]) & (fires_df["longitude"] <= PH_BOX[3])
    )
    ph_points = fires_df[ph_mask]
    ph_by_date = ph_points.groupby("date").size()
    # R over the FULL calendar (a day with zero fires is still a day; indexing
    # only observed fire dates would misalign the lag shifts).
    R_series = np.array([int(ph_by_date.get(d.isoformat(), 0)) for d in dates], dtype=float)
    del fire_dates

    # City -> distance to the stubble source point
    city_dist = {c.city_id: float(_haversine_vec(c.latitude, c.longitude,
                                                 np.array([STUBBLE_LAT]), np.array([STUBBLE_LON]))[0])
                 for c in cities}

    per_city_rows: list[list] = []
    for c in cities:
        if c.synthetic_role == "skip":
            continue
        if c.synthetic_role == "none":
            continue  # no data at all -> no rows in the master table (tier 3)
        # Stable hash (zlib.crc32): Python's hash() is salted per process and
        # would break cross-process reproducibility.
        rng = np.random.default_rng(SEED + 2 + (zlib.crc32(c.city_id.encode()) % 100000))
        base = c.synthetic_base_pm25

        mult = np.array([seasonal_multiplier(int(d)) for d in doys])
        weekly = np.array([weekly_factor(int(d)) for d in dows])

        # AR(1) lognormal noise, per city.
        e = np.empty(n_days)
        e[0] = float(rng.normal(0, 0.12))
        innov = rng.normal(0, 0.12, size=n_days)
        for t in range(1, n_days):
            e[t] = 0.6 * e[t - 1] + innov[t]

        pm25 = base * mult * weekly * np.exp(e)
        pm25 = np.maximum(pm25, 5.0)

        if c.synthetic_role == "ground":
            # Stubble contribution with the band-specific lag: use the full
            # per-day R(d) series shifted by the city's lag (Python integer
            # indexing, no wraparound).
            dist = city_dist[c.city_id]
            if dist <= STUBBLE_BANDS[0][0]:
                coeff, lag = STUBBLE_BANDS[0][1], STUBBLE_BANDS[0][2]
            elif dist <= STUBBLE_BANDS[1][0]:
                coeff, lag = STUBBLE_BANDS[1][1], STUBBLE_BANDS[1][2]
            else:
                coeff, lag = FAR_COEFF, FAR_LAG
            R_shift = np.zeros(n_days)
            R_shift[lag:] = R_series[: n_days - lag]
            f_R = 250.0 * (1.0 - np.exp(-R_shift / 120.0))
            contrib = coeff * f_R
            pm25 = np.maximum(pm25 + contrib, 5.0)

        pm10 = pm25 * 1.7 * np.exp(rng.normal(0, 0.1, size=n_days))
        no2 = 15 + 0.12 * pm25 + rng.normal(0, 4, size=n_days)
        so2 = 8 + 0.03 * pm25 + rng.normal(0, 2, size=n_days)
        co = 0.6 + 0.004 * pm25 + rng.normal(0, 0.15, size=n_days)
        o3 = 35 - 0.05 * pm25 + rng.normal(0, 6, size= n_days)

        # Weather.
        temp = 25 - 7 * np.cos(2 * np.pi * (doys - 15) / 365) + rng.normal(0, 1.5, size=n_days)
        humidity = np.clip(60 + 15 * np.sin(2 * np.pi * (doys - 200) / 365) + rng.normal(0, 8, size=n_days), 15, 100)
        pressure = 100.0 + rng.normal(0, 0.4, size=n_days)
        wind_speed = np.clip(rng.lognormal(mean=math.log(2.5), sigma=0.4, size=n_days), 0.3, 12)
        nov_jan = np.isin(months, [11, 12, 1])
        wind_speed = np.where(nov_jan, wind_speed * 0.8, wind_speed)
        wind_dir = np.array([_wind_dir_for(c.latitude, int(m), rng) for m in months])

        # Satellite columns: NaN with probability 0.15 independently per day.
        s5p_no2 = 25 + 0.5 * pm25 + rng.normal(0, 8, size=n_days)
        s5p_so2 = 20 + 0.2 * pm25 + rng.normal(0, 10, size=n_days)
        s5p_co = 28 + 0.02 * pm25 + rng.normal(0, 2, size=n_days)
        aai = 0.3 + pm25 / 120 + rng.normal(0, 0.2, size=n_days)
        for arr in (s5p_no2, s5p_so2, s5p_co, aai):
            missing = rng.random(n_days) < 0.15
            arr[missing] = np.nan

        # Per-city fire features within FIRE_RADIUS_KM (vectorized haversine:
        # ~90k fire points per city is fast; a row-wise apply is not).
        fire_lats = fires_df["latitude"].to_numpy(dtype=float)
        fire_lons = fires_df["longitude"].to_numpy(dtype=float)
        fire_dates_arr = fires_df["date"].to_numpy()
        dists = _haversine_vec(c.latitude, c.longitude, fire_lats, fire_lons)
        close_mask = dists <= FIRE_RADIUS_KM
        c_fires = pd.DataFrame({"date": fire_dates_arr[close_mask], "frp": fires_df["frp"].to_numpy()[close_mask]})
        if len(c_fires):
            fc_by_date = c_fires.groupby("date").agg(fire_count=("frp", "size"), fire_frp=("frp", "sum"))
        else:
            fc_by_date = pd.DataFrame({"fire_count": pd.Series(dtype=int), "fire_frp": pd.Series(dtype=float)})
        fire_count = np.array([int(fc_by_date["fire_count"].get(d.isoformat(), 0)) for d in dates], dtype=float)
        fire_frp = np.array([float(fc_by_date["fire_frp"].get(d.isoformat(), 0.0)) for d in dates])

        is_ground = c.synthetic_role == "ground"
        for i, d in enumerate(dates):
            row: list = [c.city_id, d.isoformat()]
            if is_ground:
                # Pollutants (floors applied); AQI filled by build step via aqi module.
                row += [
                    max(0.0, float(pm25[i])), max(0.0, float(pm10[i])),
                    max(0.0, float(no2[i])), max(0.0, float(so2[i])),
                    max(0.0, float(co[i])), max(0.0, float(o3[i])),
                    None,  # aqi placeholder, computed below
                ]
            else:
                row += [None] * 7
            row += [
                float(temp[i]), float(humidity[i]), float(pressure[i]),
                float(wind_speed[i]), float(wind_dir[i]),
                int(fire_count[i]), float(fire_frp[i]),
                None if math.isnan(s5p_no2[i]) else float(s5p_no2[i]),
                None if math.isnan(s5p_so2[i]) else float(s5p_so2[i]),
                None if math.isnan(s5p_co[i]) else float(s5p_co[i]),
                None if math.isnan(aai[i]) else float(aai[i]),
            ]
            per_city_rows.append(row)

    columns = MASTER_COLUMNS
    df = pd.DataFrame(per_city_rows, columns=columns)
    return df, fires_df
