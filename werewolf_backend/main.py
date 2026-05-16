from fastapi import FastAPI

from api.routes import router as api_router
from config.settings import get_settings
from websocket.routes import router as websocket_router

settings = get_settings()
app = FastAPI(title=settings.app_name)
app.include_router(api_router, prefix="/api")
app.include_router(websocket_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "AI Werewolf backend is running"}
