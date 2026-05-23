from fastapi import APIRouter, Request

from config import settings

router = APIRouter()


@router.get("/health")
async def health_check(request: Request) -> dict[str, str | int | bool]:
    runtime_port = request.url.port or settings.app_port
    return {
        "status": "ok",
        "app": settings.app_name,
        "port": runtime_port,
        "llm_provider": settings.llm_provider,
        "app_env": settings.app_env,
        "websocket_path": "/ws",
        "redis_configured": bool(settings.redis_host),
        "mysql_configured": bool(settings.mysql_host),
    }
