from fastapi import APIRouter, Request

from config.settings import get_settings

router = APIRouter()


@router.get("/health")
async def health_check(request: Request) -> dict[str, str | int]:
    settings = get_settings()
    runtime_port = request.url.port or settings.app_port
    return {
        "status": "ok",
        "app": settings.app_name,
        "port": runtime_port,
    }
