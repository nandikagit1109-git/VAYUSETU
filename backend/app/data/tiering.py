"""Coverage tiering (section 5.3) — computed from the data, never hardcoded.

- has_ground: >= MIN_GROUND_DAYS rows with non-null aqi or non-null pm25
- has_aux:    >= MIN_AUX_DAYS rows with non-null temp or non-null wind_speed
- tier 1 if has_ground, else 2 if has_aux, else 3

Active cities (synthetic mode): every registry city whose role is not `skip`.
Active cities (real mode): every non-skip registry city, plus any skip city
that has ground data in the loaded files.
"""
import pandas as pd

from ..config import MIN_AUX_DAYS, MIN_GROUND_DAYS


def compute_tiers(master: pd.DataFrame, cities: list, mode: str) -> dict[str, int]:
    tiers: dict[str, int] = {}
    if len(master) == 0:
        return tiers
    grouped = master.groupby("city_id")
    for city_id, g in grouped:
        ground_days = int((g["aqi"].notna() | g["pm25"].notna()).sum())
        aux_days = int((g["temp"].notna() | g["wind_speed"].notna()).sum())
        if ground_days >= MIN_GROUND_DAYS:
            tiers[city_id] = 1
        elif aux_days >= MIN_AUX_DAYS:
            tiers[city_id] = 2
        else:
            tiers[city_id] = 3
    return tiers


def active_city_ids(cities: list, master: pd.DataFrame, mode: str) -> set[str]:
    present = set(master["city_id"].unique())
    active: set[str] = set()
    for c in cities:
        if c.synthetic_role != "skip":
            active.add(c.city_id)
        elif mode == "real" and c.city_id in present:
            active.add(c.city_id)
    # Real-mode files may also contain registry cities with no data rows; they
    # stay active (tier 3) as long as they are registry members and non-skip.
    return active
