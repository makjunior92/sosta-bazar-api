from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OfferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
    title: str
    store_name: str
    store_slug: str
    price_bdt: Decimal
    unit_price_bdt: Decimal | None = None
    product_url: str
    image_url: str | None = None
    in_stock: bool = True
    scraped_at: datetime | None = None
    is_best_deal: bool = False


class SearchResponse(BaseModel):
    query: str
    area: str | None = None
    cached: bool = False
    job_id: UUID | None = None
    offers: list[OfferOut] = Field(default_factory=list)
    stores_checked: list[str] = Field(default_factory=list)
    stores_failed: list[str] = Field(default_factory=list)


class StoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    base_url: str
    is_active: bool
    health_ok: bool
    last_scraped_at: datetime | None = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    canonical_name: str
    brand: str | None = None
    category: str | None = None
    unit_label: str | None = None
    unit_size: Decimal | None = None
    offers: list[OfferOut] = Field(default_factory=list)


class PriceHistoryPoint(BaseModel):
    recorded_at: datetime
    price_bdt: Decimal
    store_name: str


class CompareResponse(BaseModel):
    offers: list[OfferOut]


class HealthResponse(BaseModel):
    status: str
    service: str


class SSEEvent(BaseModel):
    event: str
    data: dict
