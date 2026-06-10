import json
from typing import Any

import redis.asyncio as aioredis

from app.core.config import get_settings

settings = get_settings()
_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def cache_key(query: str, stores: str = "all", area: str = "") -> str:
    return f"search:{query.lower().strip()}:{stores}:{area.lower().strip()}"


async def get_cached_search(key: str) -> dict[str, Any] | None:
    client = await get_redis()
    raw = await client.get(key)
    if raw:
        return json.loads(raw)
    return None


async def set_cached_search(key: str, data: dict[str, Any], ttl: int | None = None) -> None:
    client = await get_redis()
    await client.setex(key, ttl or settings.cache_ttl_seconds, json.dumps(data, default=str))


async def publish_job_event(job_id: str, event: dict[str, Any]) -> None:
    client = await get_redis()
    await client.publish(f"search_job:{job_id}", json.dumps(event, default=str))
