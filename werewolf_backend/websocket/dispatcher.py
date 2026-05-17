from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import WebSocket

from game_engine.service import GameCommandService

logger = logging.getLogger(__name__)


class WebSocketCommandDispatcher:
    def __init__(self, command_service: GameCommandService | None = None) -> None:
        self.command_service = command_service or GameCommandService()

    async def dispatch(self, websocket: WebSocket, payload: dict[str, Any]) -> None:
        command = payload.get("cmd")
        started_at = time.perf_counter()

        if command == "GAME_START":
            player_count = payload.get("player_count")
            role_counts = payload.get("role_counts")
            assigned_roles = payload.get("assigned_roles")
            logger.info(
                "command received cmd=%s player_count=%s role_counts=%s assigned_roles=%s",
                command,
                player_count,
                role_counts,
                assigned_roles,
            )
            if not isinstance(player_count, int) or player_count <= 0:
                logger.warning("command validation failed cmd=%s reason=invalid_player_count", command)
                await websocket.send_json({"event": "ERROR", "message": "GAME_START requires positive integer player_count"})
                return
            if not isinstance(role_counts, dict):
                logger.warning("command validation failed cmd=%s reason=invalid_role_counts", command)
                await websocket.send_json({"event": "ERROR", "message": "GAME_START requires role_counts object"})
                return
            if not isinstance(assigned_roles, list):
                logger.warning("command validation failed cmd=%s reason=invalid_assigned_roles", command)
                await websocket.send_json({"event": "ERROR", "message": "GAME_START requires assigned_roles array"})
                return

            try:
                session, start_event = await self.command_service.create_game(
                    player_count=player_count,
                    role_counts=role_counts,
                    assigned_roles=assigned_roles,
                )
            except ValueError as error:
                logger.warning("command failed cmd=%s error=%s", command, error)
                await websocket.send_json({"event": "ERROR", "message": str(error)})
                return

            await websocket.send_json(start_event)
            await self.command_service.start_game_stream(session["game_id"], websocket.send_json)
            logger.info("command completed cmd=%s duration_ms=%.2f game_id=%s", command, (time.perf_counter() - started_at) * 1000, session["game_id"])
            return

        if command == "GAME_PAUSE":
            game_id = payload.get("game_id")
            logger.info("command received cmd=%s game_id=%s", command, game_id)
            if not game_id:
                logger.warning("command validation failed cmd=%s reason=missing_game_id", command)
                await websocket.send_json({"event": "ERROR", "message": "GAME_PAUSE requires game_id from GAME_STARTED"})
                return
            await websocket.send_json(await self.command_service.handle_pause(game_id))
            logger.info("command completed cmd=%s duration_ms=%.2f game_id=%s", command, (time.perf_counter() - started_at) * 1000, game_id)
            return

        if command == "GAME_STOP":
            game_id = payload.get("game_id")
            logger.info("command received cmd=%s game_id=%s", command, game_id)
            if not game_id:
                logger.warning("command validation failed cmd=%s reason=missing_game_id", command)
                await websocket.send_json({"event": "ERROR", "message": "GAME_STOP requires game_id from GAME_STARTED"})
                return
            await websocket.send_json(await self.command_service.handle_stop(game_id))
            logger.info("command completed cmd=%s duration_ms=%.2f game_id=%s", command, (time.perf_counter() - started_at) * 1000, game_id)
            return

        if command == "GAME_RESET":
            game_id = payload.get("game_id")
            logger.info("command received cmd=%s game_id=%s", command, game_id)
            await websocket.send_json(await self.command_service.handle_reset(game_id if isinstance(game_id, str) and game_id else None))
            logger.info("command completed cmd=%s duration_ms=%.2f game_id=%s", command, (time.perf_counter() - started_at) * 1000, game_id)
            return

        logger.warning("unsupported command cmd=%s", command)
        await websocket.send_json({"event": "ERROR", "message": f"Unsupported command: {command}"})
