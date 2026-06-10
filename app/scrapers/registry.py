from app.scrapers.base import StoreAdapter
from app.scrapers.chaldal import ChaldalAdapter
from app.scrapers.daraz_dmart import DarazDmartAdapter
from app.scrapers.meenaclick import MeenaClickAdapter
from app.scrapers.shwapno import ShwapnoAdapter

ADAPTERS: dict[str, type[StoreAdapter]] = {
    "chaldal": ChaldalAdapter,
    "shwapno": ShwapnoAdapter,
    "meenaclick": MeenaClickAdapter,
    "daraz-dmart": DarazDmartAdapter,
}

STORE_SEED = [
    {"name": "Chaldal", "slug": "chaldal", "base_url": "https://chaldal.com", "adapter_key": "chaldal"},
    {"name": "Shwapno", "slug": "shwapno", "base_url": "https://www.shwapno.com", "adapter_key": "shwapno"},
    {"name": "MeenaClick", "slug": "meenaclick", "base_url": "https://meenabazaronline.com", "adapter_key": "meenaclick"},
    {"name": "Daraz dMart", "slug": "daraz-dmart", "base_url": "https://www.daraz.com.bd/dmart/", "adapter_key": "daraz-dmart"},
]


def get_adapter(adapter_key: str) -> StoreAdapter:
    cls = ADAPTERS.get(adapter_key)
    if not cls:
        raise ValueError(f"Unknown adapter: {adapter_key}")
    return cls()


def get_adapters_for_stores(store_filter: str = "all") -> list[StoreAdapter]:
    if store_filter == "all":
        return [cls() for cls in ADAPTERS.values()]
    slugs = [s.strip() for s in store_filter.split(",") if s.strip()]
    return [ADAPTERS[s]() for s in slugs if s in ADAPTERS]
