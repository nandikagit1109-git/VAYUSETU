"""DataStore singleton (section 12): populated once at startup, read-only after.

Holds the master dataframe, fires dataframe, registry, tiers and DEMO_NOW.
Request handlers must never mutate these frames or reload the CSV per request.
"""
import logging
import threading

import pandas as pd

from .config import DATA_MODE
from .data import build_master, registry, synthetic, tiering
from .data.registry import CityEntry

logger = logging.getLogger("vayusetu.store")


class DataStore:
    _instance: "DataStore | None" = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self.cities: list[CityEntry] = []
        self.city_by_id: dict[str, CityEntry] = {}
        self.zones: list[dict] = []
        self.master: pd.DataFrame | None = None
        self.fires: pd.DataFrame | None = None
        self.tiers: dict[str, int] = {}
        self.active_ids: set[str] = set()
        self.demo_now: str | None = None
        self.data_mode: str = DATA_MODE
        self.fallback_reason: str | None = None

    @classmethod
    def instance(cls) -> "DataStore":
        with cls._lock:
            if cls._instance is None:
                inst = DataStore()
                inst.load()
                cls._instance = inst
            return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Test hook: drop the singleton so the next instance() reloads."""
        with cls._lock:
            cls._instance = None

    def _finalize_synthetic(self, master: pd.DataFrame) -> pd.DataFrame:
        """Compute AQI for synthetic rows (max of PM2.5/PM10 sub-indices)."""
        from .services.aqi import compute_aqi

        aqis = []
        for pm25, pm10 in zip(master["pm25"], master["pm10"]):
            aqi = compute_aqi(
                None if pd.isna(pm25) else float(pm25),
                None if pd.isna(pm10) else float(pm10),
            )
            aqis.append(round(aqi, 1) if aqi is not None else None)
        master["aqi"] = aqis
        return master

    def _compute_demo_now(self, master: pd.DataFrame) -> str:
        if self.data_mode == "real":
            with_ground = master[master["aqi"].notna()]
            if len(with_ground):
                return str(with_ground["date"].max())
        return synthetic.DEMO_NOW.isoformat()

    def load(self) -> None:
        self.cities = registry.load_cities()
        self.city_by_id = {c.city_id: c for c in self.cities}
        self.zones = registry.load_industrial_zones()

        fallback_reason: str | None = None
        if self.data_mode == "synthetic":
            if build_master.needs_rebuild():
                master, fires = synthetic.generate(self.cities)
                master = self._finalize_synthetic(master)
                build_master.write_processed(master, fires)
                logger.info("synthetic master built: %d rows, %d cities",
                            len(master), master["city_id"].nunique())
            else:
                master = build_master.load_master()
                fires = build_master.load_fires()
        else:
            from .data import real_loader

            try:
                master, fires = real_loader.build_real_frames(self.cities)
                build_master.write_processed(master, fires)
            except Exception as exc:
                fallback_reason = f"real data unavailable: {exc}"
                logger.warning("real mode failed (%s); falling back to synthetic", exc)
                if build_master.needs_rebuild():
                    master, fires = synthetic.generate(self.cities)
                    master = self._finalize_synthetic(master)
                    build_master.write_processed(master, fires)
                else:
                    master = build_master.load_master()
                    fires = build_master.load_fires()

        self.master = master
        self.fires = fires
        self.tiers = tiering.compute_tiers(master, self.cities, self.data_mode)
        self.active_ids = tiering.active_city_ids(self.cities, master, self.data_mode)
        self.fallback_reason = fallback_reason
        self.demo_now = self._compute_demo_now(master)

    # --- convenience read-only accessors ---

    def active_cities(self) -> list[CityEntry]:
        return [c for c in self.cities if c.city_id in self.active_ids]

    def city(self, city_id: str) -> CityEntry | None:
        return self.city_by_id.get(city_id)

    def tier_of(self, city_id: str) -> int:
        return self.tiers.get(city_id, 3)

    def latest_aqi(self, city_id: str) -> tuple[float | None, str | None]:
        g = self.master[self.master["city_id"] == city_id]
        if g.empty:
            return None, None
        g = g[g["aqi"].notna()]
        if g.empty:
            return None, None
        row = g.loc[g["date"].idxmax()]
        return float(row["aqi"]), str(row["date"])

    def history(self, city_id: str, days: int) -> list[dict]:
        g = self.master[self.master["city_id"] == city_id]
        if g.empty:
            return []
        g = g[g["date"] <= self.demo_now].sort_values("date").tail(days)
        points: list[dict] = []
        for _, r in g.iterrows():
            aqi = None if pd.isna(r["aqi"]) else round(float(r["aqi"]), 1)
            pm25 = None if pd.isna(r["pm25"]) else round(float(r["pm25"]), 1)
            points.append({"date": str(r["date"]), "aqi": aqi, "pm25": pm25})
        return points
