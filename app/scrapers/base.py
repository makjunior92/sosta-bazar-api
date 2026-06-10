from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class RawOffer:
    title: str
    price_bdt: Decimal
    product_url: str
    image_url: str | None = None
    external_id: str | None = None
    in_stock: bool = True
    unit_price_bdt: Decimal | None = None
    raw_data: dict = field(default_factory=dict)


class StoreAdapter(ABC):
    store_slug: str
    store_name: str

    @abstractmethod
    async def search(self, query: str, area: str | None = None) -> list[RawOffer]:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...
