from __future__ import annotations

import json
import logging
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from websocket.dispatcher import WebSocketCommandDispatcher

router = APIRouter()
dispatcher = WebSocketCommandDispatcher()
logger = logging.getLogger(__name__)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    connection_id = uuid4().hex[:8]
    client_host = websocket.client.host if websocket.client else "unknown"
    await websocket.accept()
    logger.info("websocket connected connection_id=%s client_host=%s", connection_id, client_host)
    await websocket.send_json({"event": "CONNECTED", "message": "WebSocket ready"})
    try:
        while True:
            raw_payload = await websocket.receive_text()
            logger.info("websocket message received connection_id=%s payload_bytes=%s", connection_id, len(raw_payload.encode("utf-8")))
            try:
                payload = json.loads(raw_payload)
            except json.JSONDecodeError:
                logger.warning("websocket invalid json connection_id=%s", connection_id)
                await websocket.send_json({"event": "ERROR", "message": "Invalid JSON payload"})
                continue

            if not isinstance(payload, dict):
                logger.warning("websocket invalid payload type connection_id=%s payload_type=%s", connection_id, type(payload).__name__)
                await websocket.send_json({"event": "ERROR", "message": "Payload must be a JSON object"})
                continue

            logger.info("websocket dispatch start connection_id=%s cmd=%s", connection_id, payload.get("cmd"))
            await dispatcher.dispatch(websocket, payload)
    except WebSocketDisconnect:
        logger.info("websocket disconnected connection_id=%s", connection_id)
        return
