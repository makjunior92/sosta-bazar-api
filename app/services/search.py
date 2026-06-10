import asyncio
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import cache_key, get_cached_search, publish_job_event, set_cached_search
from app.models import Offer, PriceSnapshot, Product, SearchJob, SearchJobStatus, SearchResult, Store
from app.scrapers.base import RawOffer
from app.scrapers.registry import STORE_SEED, get_adapters_for_stores
from app.services.matching import enrich_offer, mark_best_deals
from app.services.unit_price import extract_unit_info

logger = structlog.get_logger()


async def seed_stores(db: AsyncSession) -> None:
    for data in STORE_SEED:
        existing = await db.scalar(select(Store).where(Store.slug == data["slug"]))
        if not existing:
            db.add(Store(**data))
    await db.commit()


def _json_safe(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value


def raw_to_dict(offer: RawOffer, store_name: str, store_slug: str) -> dict:
    enriched = enrich_offer(offer)
    return _json_safe(
        {
            "title": enriched.title,
            "store_name": store_name,
            "store_slug": store_slug,
            "price_bdt": enriched.price_bdt,
            "unit_price_bdt": enriched.unit_price_bdt,
            "product_url": enriched.product_url,
            "image_url": enriched.image_url,
            "in_stock": enriched.in_stock,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "is_best_deal": False,
        }
    )


async def scrape_all_stores(
    query: str,
    area: str | None,
    store_filter: str = "all",
    job_id: str | None = None,
) -> tuple[list[dict], list[str], list[str]]:
    adapters = get_adapters_for_stores(store_filter)
    all_offers: list[dict] = []
    checked: list[str] = []
    failed: list[str] = []

    async def scrape_one(adapter):
        try:
            if job_id:
                await publish_job_event(job_id, {"event": "store_start", "store": adapter.store_slug})
            results = await adapter.search(query, area)
            checked.append(adapter.store_slug)
            offers = [raw_to_dict(r, adapter.store_name, adapter.store_slug) for r in results]
            if job_id:
                await publish_job_event(
                    job_id,
                    {"event": "store_done", "store": adapter.store_slug, "count": len(offers)},
                )
            return offers
        except Exception as exc:
            logger.exception("scrape_failed", store=adapter.store_slug, error=str(exc))
            failed.append(adapter.store_slug)
            if job_id:
                await publish_job_event(
                    job_id,
                    {"event": "store_error", "store": adapter.store_slug, "error": str(exc)},
                )
            return []

    results = await asyncio.gather(*[scrape_one(a) for a in adapters])
    for batch in results:
        all_offers.extend(batch)

    return mark_best_deals(all_offers), checked, failed


async def persist_search_results(
    db: AsyncSession,
    job: SearchJob,
    offers: list[dict],
) -> None:
    for item in offers:
        store = await db.scalar(select(Store).where(Store.slug == item["store_slug"]))
        if not store:
            continue
        db.add(
            SearchResult(
                job_id=job.id,
                store_slug=item["store_slug"],
                title=item["title"],
                price_bdt=Decimal(str(item["price_bdt"])),
                unit_price_bdt=Decimal(str(item["unit_price_bdt"])) if item.get("unit_price_bdt") else None,
                product_url=item["product_url"],
                image_url=item.get("image_url"),
                in_stock=item.get("in_stock", True),
                is_best_deal=item.get("is_best_deal", False),
            )
        )
        label, size = extract_unit_info(item["title"])
        product = Product(
            canonical_name=item["title"],
            unit_label=label,
            unit_size=size,
            search_keywords=job.query,
        )
        db.add(product)
        await db.flush()
        offer = Offer(
            product_id=product.id,
            store_id=store.id,
            title=item["title"],
            price_bdt=Decimal(str(item["price_bdt"])),
            unit_price_bdt=Decimal(str(item["unit_price_bdt"])) if item.get("unit_price_bdt") else None,
            product_url=item["product_url"],
            image_url=item.get("image_url"),
            in_stock=item.get("in_stock", True),
            raw_data=item,
        )
        db.add(offer)
        await db.flush()
        db.add(PriceSnapshot(offer_id=offer.id, price_bdt=offer.price_bdt))
        store.last_scraped_at = datetime.now(timezone.utc)
    job.status = SearchJobStatus.completed
    job.completed_at = datetime.now(timezone.utc)
    await db.commit()


async def run_search(
    db: AsyncSession,
    query: str,
    area: str | None = None,
    store_filter: str = "all",
    force_refresh: bool = False,
) -> dict:
    key = cache_key(query, store_filter, area or "")
    if not force_refresh:
        cached = await get_cached_search(key)
        if cached:
            cached["cached"] = True
            return cached

    job = SearchJob(query=query, area=area, status=SearchJobStatus.running)
    db.add(job)
    await db.commit()
    await db.refresh(job)

    offers, checked, failed = await scrape_all_stores(query, area, store_filter, str(job.id))
    await persist_search_results(db, job, offers)

    payload = {
        "query": query,
        "area": area,
        "cached": False,
        "job_id": str(job.id),
        "offers": offers,
        "stores_checked": checked,
        "stores_failed": failed,
    }
    await set_cached_search(key, payload)
    return payload


async def get_deals(db: AsyncSession, limit: int = 20) -> list[dict]:
    result = await db.execute(
        select(SearchResult)
        .where(SearchResult.is_best_deal.is_(True))
        .order_by(SearchResult.price_bdt.asc())
        .limit(limit)
    )
    rows = result.scalars().all()
    deals = []
    for r in rows:
        store = await db.scalar(select(Store).where(Store.slug == r.store_slug))
        deals.append(
            {
                "title": r.title,
                "store_name": store.name if store else r.store_slug,
                "store_slug": r.store_slug,
                "price_bdt": r.price_bdt,
                "unit_price_bdt": r.unit_price_bdt,
                "product_url": r.product_url,
                "image_url": r.image_url,
                "in_stock": r.in_stock,
                "is_best_deal": True,
            }
        )
    return deals
