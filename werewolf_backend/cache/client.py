from __future__ import annotations

from redis.asyncio import Redis

from config import settings


async def get_redis_client() -> Redis:
    return Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)


async def close_redis_client() -> None:
    return None
