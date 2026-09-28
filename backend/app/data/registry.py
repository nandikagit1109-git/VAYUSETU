"""City + industrial-zone registry loading (section 5.1)."""
import csv
import logging
from dataclasses import dataclass

from ..config import DATA_DIR

logger = logging.getLogger("vayusetu.registry")

ROLES = ("ground", "aux_only", "none", "skip")


@dataclass
class CityEntry:
    city_id: str
    name: str
    state: str
    latitude: float
    longitude: float
    synthetic_role: str
    synthetic_base_pm25: float
    ncr: int


REQUIRED_CITY_COLUMNS = [
    "city_id", "name", "state", "latitude", "longitude", "synthetic_role", "synthetic_base_pm25", "ncr",
]
REQUIRED_ZONE_COLUMNS = ["zone_id", "name", "latitude", "longitude"]


def load_cities() -> list[CityEntry]:
    path = DATA_DIR / "cities.csv"
    cities: list[CityEntry] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [c for c in REQUIRED_CITY_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"cities.csv missing columns: {missing}")
        for row in reader:
            role = row["synthetic_role"].strip()
            if role not in ROLES:
                logger.warning("cities.csv: unknown synthetic_role '%s' for %s; treating as skip", role, row["city_id"])
                role = "skip"
            cities.append(CityEntry(
                city_id=row["city_id"].strip(),
                name=row["name"].strip(),
                state=row["state"].strip(),
                latitude=float(row["latitude"]),
                longitude=float(row["longitude"]),
                synthetic_role=role,
                synthetic_base_pm25=float(row["synthetic_base_pm25"]),
                ncr=int(row["ncr"]),
            ))
    if not cities:
        raise ValueError("cities.csv contains no cities")
    return cities


def load_industrial_zones() -> list[dict]:
    path = DATA_DIR / "industrial_zones.csv"
    zones: list[dict] = []
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            missing = [c for c in REQUIRED_ZONE_COLUMNS if c not in (reader.fieldnames or [])]
            if missing:
                raise ValueError(f"industrial_zones.csv missing columns: {missing}")
            for row in reader:
                zones.append({
                    "zone_id": row["zone_id"].strip(),
                    "name": row["name"].strip(),
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),
                })
    except Exception as exc:
        logger.warning("could not load industrial zones (%s); continuing without them", exc)
        return []
    return zones
