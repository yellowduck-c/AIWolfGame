from fastapi import APIRouter, WebSocket

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    await websocket.send_json({"event": "CONNECTED", "message": "WebSocket ready"})
    try:
        while True:
            payload = await websocket.receive_text()
            await websocket.send_json({"event": "ECHO", "payload": payload})
    except Exception:
        await websocket.close()
