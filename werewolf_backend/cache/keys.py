from config import settings


def game_session_key(game_id: str) -> str:
    return f"{settings.redis_prefix}:game:{game_id}:session"


def game_event_log_key(game_id: str) -> str:
    return f"{settings.redis_prefix}:game:{game_id}:events"
