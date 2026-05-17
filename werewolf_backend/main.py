import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router as api_router
from cache.client import close_redis_client
from config import settings
from utils.logging import configure_logging
from websocket.routes import router as websocket_router

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173", "http://127.0.0.1:5174", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix="/api")
app.include_router(websocket_router)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    logger.info("backend shutdown: closing redis client")
    await close_redis_client()


@app.get("/")
async def root() -> dict[str, str]:
    logger.info("root health route accessed")
    return {"message": "AI Werewolf backend is running"}
