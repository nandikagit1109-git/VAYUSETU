"""/api/meta and /health (section 11.3)."""
from fastapi import APIRouter

from ..schemas import Meta
from ..store import DataStore

router = APIRouter(prefix="/api/meta", tags=["meta"])


def build_meta(store: DataStore) -> Meta:
    version, _ = _model_state()
    tier1 = sum(1 for c in store.active_cities() if store.tier_of(c.city_id) == 1)
    tier2 = sum(1 for c in store.active_cities() if store.tier_of(c.city_id) == 2)
    tier3 = sum(1 for c in store.active_cities() if store.tier_of(c.city_id) == 3)
    from ..federated.runner import read_status

    fl_status = read_status().get("status", "idle")
    has_model = version is not None
    return Meta(
        data_mode=store.data_mode,  # type: ignore[arg-type]
        fallback_reason=store.fallback_reason,
        demo_now=store.demo_now or "",
        n_cities=len(store.active_cities()),
        n_tier1=tier1,
        n_tier2=tier2,
        n_tier3=tier3,
        model_version=version,
        model_method="federated_gru" if has_model else "persistence",
        fl_status=fl_status,  # type: ignore[arg-type]
    )


def _model_state():
    from ..services.forecast_service import model_info

    return model_info()


@router.get("")
def get_meta():
    store = DataStore.instance()
    return build_meta(store)
