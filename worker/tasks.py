import asyncio

from worker.celery_app import celery_app


def run_async(coro):
    return asyncio.run(coro)


@celery_app.task(name="worker.tasks.refresh_popular_searches")
def refresh_popular_searches():
    async def _run():
        from sqlalchemy.ext.asyncio import AsyncSession

        from app.core.database import AsyncSessionLocal
        from app.services.search import run_search, seed_stores

        queries = ["rice", "milk", "egg", "oil", "sugar", "butter", "onion", "potato"]
        async with AsyncSessionLocal() as db:
            await seed_stores(db)
            for q in queries:
                await run_search(db, q, force_refresh=True)

    run_async(_run())


@celery_app.task(name="worker.tasks.run_search_job")
def run_search_job(query: str, area: str | None = None, stores: str = "all"):
    async def _run():
        from app.core.database import AsyncSessionLocal
        from app.services.search import run_search, seed_stores

        async with AsyncSessionLocal() as db:
            await seed_stores(db)
            return await run_search(db, query, area, stores, force_refresh=True)

    return run_async(_run())


@celery_app.task(name="worker.tasks.health_check_stores")
def health_check_stores():
    async def _run():
        from sqlalchemy import select

        from app.core.database import AsyncSessionLocal
        from app.models import Store
        from app.scrapers.registry import ADAPTERS

        async with AsyncSessionLocal() as db:
            stores = (await db.execute(select(Store))).scalars().all()
            for store in stores:
                adapter_cls = ADAPTERS.get(store.adapter_key)
                if adapter_cls:
                    adapter = adapter_cls()
                    store.health_ok = await adapter.health_check()
            await db.commit()

    run_async(_run())
