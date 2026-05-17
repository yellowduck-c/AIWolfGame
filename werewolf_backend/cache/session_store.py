from __future__ import annotations

from typing import Any

from cache.client import get_redis_client
from cache.keys import game_event_log_key, game_session_key
from cache.serializers import dumps_event_log, dumps_session, loads_event_log, loads_session

SESSION_TTL_SECONDS = 60 * 60 * 6


class GameSessionStore:
    async def create_session(self, game_id: str, session: dict[str, Any]) -> dict[str, Any]:
        redis = await get_redis_client()
        key = game_session_key(game_id)
        await redis.set(key, dumps_session(session), ex=SESSION_TTL_SECONDS)
        return session

    async def get_session(self, game_id: str) -> dict[str, Any] | None:
        redis = await get_redis_client()
        key = game_session_key(game_id)
        payload = await redis.get(key)
        return loads_session(payload)

    async def update_session(self, game_id: str, session: dict[str, Any]) -> dict[str, Any]:
        redis = await get_redis_client()
        key = game_session_key(game_id)
        await redis.set(key, dumps_session(session), ex=SESSION_TTL_SECONDS)
        return session

    async def delete_session(self, game_id: str) -> None:
        redis = await get_redis_client()
        key = game_session_key(game_id)
        await redis.delete(key)

    async def initialize_event_log(self, game_id: str) -> None:
        redis = await get_redis_client()
        key = game_event_log_key(game_id)
        await redis.set(key, dumps_event_log([]), ex=SESSION_TTL_SECONDS)

    async def append_event(self, game_id: str, event: dict[str, Any]) -> dict[str, Any]:
        redis = await get_redis_client()
        key = game_event_log_key(game_id)
        current_events = loads_event_log(await redis.get(key))
        current_events.append(event)
        await redis.set(key, dumps_event_log(current_events), ex=SESSION_TTL_SECONDS)
        return event

    async def get_events(self, game_id: str) -> list[dict[str, Any]]:
        redis = await get_redis_client()
        key = game_event_log_key(game_id)
        payload = await redis.get(key)
        return loads_event_log(payload)

    async def clear_events(self, game_id: str) -> None:
        redis = await get_redis_client()
        key = game_event_log_key(game_id)
        await redis.delete(key)
