import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.redis_client import get_redis
from app.models import Offer, Product, SearchJob, Store
from app.schemas import CompareResponse, HealthResponse, OfferOut, ProductOut, SearchResponse, StoreOut
from app.services.search import get_deals, run_search, scrape_all_stores, seed_stores

router = APIRouter()


@router.get("/search", response_model=SearchResponse)
async def search_products(
    q: str = Query(..., min_length=1),
    area: str | None = None,
    stores: str = "all",
    sort: str = "unit_price",
    force_refresh: bool = False,
    db: AsyncSession = Depends(get_db),
):
    await seed_stores(db)
    data = await run_search(db, q, area, stores, force_refresh)
    offers = data.get("offers", [])
    if sort == "price":
        offers = sorted(offers, key=lambda o: (o.get("price_bdt"), o.get("unit_price_bdt") or 0))
    elif sort == "freshness":
        offers = sorted(offers, key=lambda o: o.get("scraped_at", ""), reverse=True)
    else:
        offers = sorted(
            offers,
            key=lambda o: (o.get("unit_price_bdt") or o.get("price_bdt"), o.get("price_bdt")),
        )
    data["offers"] = offers
    return SearchResponse(**data)


@router.get("/search/stream")
async def search_stream(
    q: str = Query(..., min_length=1),
    area: str | None = None,
    stores: str = "all",
    db: AsyncSession = Depends(get_db),
):
    await seed_stores(db)
    job_id = str(__import__("uuid").uuid4())

    async def event_generator():
        yield f"data: {json.dumps({'event': 'started', 'job_id': job_id})}\n\n"
        offers, checked, failed = await scrape_all_stores(q, area, stores, job_id)
        payload = {
            "event": "complete",
            "query": q,
            "offers": offers,
            "stores_checked": checked,
            "stores_failed": failed,
        }
        yield f"data: {json.dumps(payload, default=str)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/deals")
async def list_deals(limit: int = 20, db: AsyncSession = Depends(get_db)):
    await seed_stores(db)
    deals = await get_deals(db, limit)
    return {"deals": deals}


@router.get("/stores", response_model=list[StoreOut])
async def list_stores(db: AsyncSession = Depends(get_db)):
    await seed_stores(db)
    result = await db.execute(select(Store).order_by(Store.name))
    return result.scalars().all()


@router.get("/products/{product_id}", response_model=ProductOut)
async def get_product(product_id: UUID, db: AsyncSession = Depends(get_db)):
    product = await db.scalar(
        select(Product).where(Product.id == product_id).options(selectinload(Product.offers))
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    offer_rows = []
    for offer in product.offers:
        store = await db.get(Store, offer.store_id)
        offer_rows.append(
            OfferOut(
                id=offer.id,
                title=offer.title,
                store_name=store.name if store else "",
                store_slug=store.slug if store else "",
                price_bdt=offer.price_bdt,
                unit_price_bdt=offer.unit_price_bdt,
                product_url=offer.product_url,
                image_url=offer.image_url,
                in_stock=offer.in_stock,
                scraped_at=offer.scraped_at,
            )
        )
    return ProductOut(
        id=product.id,
        canonical_name=product.canonical_name,
        brand=product.brand,
        category=product.category,
        unit_label=product.unit_label,
        unit_size=product.unit_size,
        offers=offer_rows,
    )


@router.get("/products/{product_id}/history")
async def product_history(product_id: UUID, db: AsyncSession = Depends(get_db)):
    from app.models import PriceSnapshot

    offers = (await db.execute(select(Offer).where(Offer.product_id == product_id))).scalars().all()
    history = []
    for offer in offers:
        store = await db.get(Store, offer.store_id)
        snaps = (
            await db.execute(
                select(PriceSnapshot)
                .where(PriceSnapshot.offer_id == offer.id)
                .order_by(PriceSnapshot.recorded_at.asc())
            )
        ).scalars().all()
        for snap in snaps:
            history.append(
                {
                    "recorded_at": snap.recorded_at,
                    "price_bdt": snap.price_bdt,
                    "store_name": store.name if store else "",
                }
            )
    return {"history": history}


@router.get("/compare", response_model=CompareResponse)
async def compare_offers(ids: str = Query(...), db: AsyncSession = Depends(get_db)):
    id_list = [UUID(x.strip()) for x in ids.split(",") if x.strip()]
    offers_out = []
    for oid in id_list:
        offer = await db.get(Offer, oid)
        if offer:
            store = await db.get(Store, offer.store_id)
            offers_out.append(
                OfferOut(
                    id=offer.id,
                    title=offer.title,
                    store_name=store.name if store else "",
                    store_slug=store.slug if store else "",
                    price_bdt=offer.price_bdt,
                    unit_price_bdt=offer.unit_price_bdt,
                    product_url=offer.product_url,
                    image_url=offer.image_url,
                    in_stock=offer.in_stock,
                    scraped_at=offer.scraped_at,
                )
            )
    return CompareResponse(offers=offers_out)
