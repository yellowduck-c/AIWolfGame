from __future__ import annotations

from redis.asyncio import Redis

from config import settings


async def get_redis_client() -> Redis:
    return Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password or None,
        db=settings.redis_db,
        encoding="utf-8",
        decode_responses=True,
    )


async def close_redis_client() -> None:
    return None
