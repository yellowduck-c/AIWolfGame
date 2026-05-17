from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from agent.core.factory import build_agent
from agent.core.registry import agent_registry
from cache.session_store import GameSessionStore
from game_engine.events import enrich_persisted_event
from game_engine.executor import PhaseDrivenExecutor
from game_engine.models import GameSession
from game_engine.state_machine import GameStateMachine

DEFAULT_PLAYER_COUNT = 6
ROLE_KEY_TO_META: dict[str, tuple[str, str]] = {
    "werewolf": ("狼人", "狼人"),
    "seer": ("预言家", "好人"),
    "witch": ("女巫", "好人"),
    "hunter": ("猎人", "好人"),
    "idiot": ("白痴", "好人"),
    "villager": ("村民", "好人"),
}
ROLE_ORDER = ["werewolf", "seer", "witch", "hunter", "idiot", "villager"]
PERSISTED_EVENT_TYPES = {
    "AGENT_SPEAK",
    "AGENT_VOTE",
    "AGENT_SKILL",
    "AGENT_STATUS_CHANGE",
    "PHASE_CHANGE",
    "GAME_OVER",
}
logger = logging.getLogger(__name__)


EventSender = Callable[[dict[str, Any]], Awaitable[None]]



def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()



def build_mock_agents(
    player_count: int = DEFAULT_PLAYER_COUNT,
    role_counts: dict[str, int] | None = None,
    assigned_roles: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    agents: list[dict[str, Any]] = []

    if assigned_roles is not None:
        if len(assigned_roles) != player_count:
            raise ValueError("player_count does not match assigned_roles total")
        assigned_roles_by_id = sorted(assigned_roles, key=lambda item: item["id"])
        for expected_id, assigned_role in enumerate(assigned_roles_by_id, start=1):
            if assigned_role.get("id") != expected_id:
                raise ValueError("assigned_roles ids must start at 1 and be contiguous")
            role_key = assigned_role.get("role_key")
            if role_key not in ROLE_KEY_TO_META:
                raise ValueError(f"unsupported role_key: {role_key}")
            role, camp = ROLE_KEY_TO_META[role_key]
            agents.append({
                "id": expected_id,
                "role": role,
                "camp": camp,
                "status": "alive",
            })
        if role_counts is not None:
            expected_role_counts = {role_key: 0 for role_key in ROLE_ORDER}
            for assigned_role in assigned_roles_by_id:
                expected_role_counts[assigned_role["role_key"]] += 1
            if expected_role_counts != {role_key: role_counts.get(role_key, 0) for role_key in ROLE_ORDER}:
                raise ValueError("assigned_roles does not match role_counts")
        return agents

    if role_counts is None:
        role_cycle = [
            ("狼人", "狼人"),
            ("狼人", "狼人"),
            ("预言家", "好人"),
            ("女巫", "好人"),
            ("猎人", "好人"),
            ("村民", "好人"),
            ("村民", "好人"),
            ("村民", "好人"),
            ("村民", "好人"),
            ("村民", "好人"),
            ("村民", "好人"),
            ("村民", "好人"),
        ]
        for index in range(player_count):
            role, camp = role_cycle[index]
            agents.append({
                "id": index + 1,
                "role": role,
                "camp": camp,
                "status": "alive",
            })
        return agents

    role_sequence: list[tuple[str, str]] = []
    for role_key in ROLE_ORDER:
        role, camp = ROLE_KEY_TO_META[role_key]
        role_sequence.extend([(role, camp)] * role_counts.get(role_key, 0))

    if len(role_sequence) != player_count:
        raise ValueError("player_count does not match role_counts total")

    for index, (role, camp) in enumerate(role_sequence, start=1):
        agents.append({
            "id": index,
            "role": role,
            "camp": camp,
            "status": "alive",
        })
    return agents



def build_game_started_event(session: GameSession) -> dict[str, Any]:
    return {"event": "GAME_STARTED", "game_id": session["game_id"], "agents": session["agents"]}



def build_game_over_event(session: GameSession) -> dict[str, Any]:
    return {"event": "GAME_OVER", "winner": session["winner"] or "unknown", "game_id": session["game_id"]}



def build_game_reset_event(game_id: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"event": "GAME_RESET", "message": "对局已重置，可重新开始。"}
    if game_id is not None:
        payload["game_id"] = game_id
    return payload



def build_runtime_agents(session: GameSession) -> dict[int, Any]:
    runtime_agents: dict[int, Any] = {}
    for agent_snapshot in session["agents"]:
        runtime_agents[agent_snapshot["id"]] = build_agent(
            player_id=agent_snapshot["id"],
            role=agent_snapshot["role"],
            camp=agent_snapshot["camp"],
        )
    return runtime_agents


class GameCommandService:
    def __init__(
        self,
        session_store: GameSessionStore | None = None,
        state_machine: GameStateMachine | None = None,
        executor: PhaseDrivenExecutor | None = None,
    ) -> None:
        self.session_store = session_store or GameSessionStore()
        self.state_machine = state_machine or GameStateMachine()
        self.executor = executor or PhaseDrivenExecutor(self.state_machine)
        self._active_game_id: str | None = None
        self._active_run_task: asyncio.Task[None] | None = None

    def _build_session_overview(
        self,
        session: GameSession,
        *,
        player_count: int,
        role_counts: dict[str, int] | None,
        created_at: str,
        started_at: str | None = None,
        ended_at: str | None = None,
    ) -> dict[str, Any]:
        return {
            "game_id": session["game_id"],
            "phase": session["phase"],
            "round": session["round"],
            "status": session["status"],
            "agents": session["agents"],
            "winner": session["winner"],
            "player_count": player_count,
            "role_counts": role_counts or {},
            "created_at": created_at,
            "started_at": started_at,
            "ended_at": ended_at,
        }

    def _runtime_session_from_snapshot(self, stored_session: dict[str, Any]) -> GameSession:
        return {
            "game_id": stored_session["game_id"],
            "phase": stored_session["phase"],
            "round": stored_session["round"],
            "status": stored_session["status"],
            "agents": stored_session["agents"],
            "winner": stored_session["winner"],
            "public_events": [],
        }

    async def _cancel_active_run_task(self) -> None:
        task = self._active_run_task
        if task is None:
            return
        self._active_run_task = None
        if task.done():
            return
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    async def _archive_game_state(self, game_id: str, *, clear_runtime_agents: bool = True) -> None:
        if clear_runtime_agents:
            agent_registry.clear_game(game_id)
        if self._active_game_id == game_id:
            self._active_game_id = None
            self._active_run_task = None

    async def _persist_session_state(self, session: GameSession) -> dict[str, Any] | None:
        stored_session = await self.session_store.get_session(session["game_id"])
        if stored_session is None:
            return None
        updated_session = {
            **stored_session,
            "phase": session["phase"],
            "round": session["round"],
            "status": session["status"],
            "agents": session["agents"],
            "winner": session["winner"],
        }
        if session["status"] == "finished" and not updated_session.get("ended_at"):
            updated_session["ended_at"] = _timestamp()
        await self.session_store.update_session(session["game_id"], updated_session)
        return updated_session

    async def _append_persisted_event(self, session: GameSession, event: dict[str, Any]) -> dict[str, Any] | None:
        if event.get("event") not in PERSISTED_EVENT_TYPES:
            return None
        persisted_event = enrich_persisted_event(session, event)
        await self.session_store.append_event(session["game_id"], persisted_event)
        return persisted_event

    async def create_game(
        self,
        player_count: int = DEFAULT_PLAYER_COUNT,
        role_counts: dict[str, int] | None = None,
        assigned_roles: list[dict[str, Any]] | None = None,
    ) -> tuple[GameSession, dict[str, Any]]:
        if self._active_game_id is not None:
            await self._cancel_active_run_task()
            await self._archive_game_state(self._active_game_id)

        created_at = _timestamp()
        game_id = uuid4().hex
        session = self.state_machine.create_initial_session(
            game_id=game_id,
            agents=build_mock_agents(player_count=player_count, role_counts=role_counts, assigned_roles=assigned_roles),
        )
        session_overview = self._build_session_overview(
            session,
            player_count=player_count,
            role_counts=role_counts,
            created_at=created_at,
        )
        logger.info(
            "game created game_id=%s player_count=%s role_counts=%s",
            game_id,
            player_count,
            role_counts,
        )
        agent_registry.register_game_agents(game_id, build_runtime_agents(session))
        logger.info("runtime agents registered game_id=%s agent_count=%s", game_id, len(session["agents"]))
        await self.session_store.create_session(game_id, session_overview)
        await self.session_store.initialize_event_log(game_id)
        self._active_game_id = game_id
        return session, build_game_started_event(session)

    async def run_game(self, game_id: str) -> tuple[GameSession, list[dict[str, Any]]]:
        stored_session = await self.session_store.get_session(game_id)
        if stored_session is None:
            raise ValueError(f"game_id {game_id} not found")

        session = self._runtime_session_from_snapshot(stored_session)
        logger.info("game run started game_id=%s phase=%s round=%s", game_id, session["phase"], session["round"])
        events: list[dict[str, Any]] = []
        for updated_session, phase_events in self.executor.iter_game(session):
            session = updated_session
            events.extend(phase_events)
            logger.info(
                "game phase emitted game_id=%s phase=%s round=%s event_count=%s status=%s",
                game_id,
                session["phase"],
                session["round"],
                len(phase_events),
                session["status"],
            )
            await self._persist_session_state(session)
            for event in phase_events:
                await self._append_persisted_event(session, event)
            if session["status"] == "finished":
                break
        logger.info("game run finished game_id=%s winner=%s total_events=%s", game_id, session["winner"], len(events))
        return session, events

    async def handle_start(
        self,
        player_count: int = DEFAULT_PLAYER_COUNT,
        role_counts: dict[str, int] | None = None,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        session, start_event = await self.create_game(player_count=player_count, role_counts=role_counts)
        session, events = await self.run_game(session["game_id"])
        return start_event, events

    async def stream_game_events(self, game_id: str):
        stored_session = await self.session_store.get_session(game_id)
        if stored_session is None:
            raise ValueError(f"game_id {game_id} not found")

        session = self._runtime_session_from_snapshot(stored_session)
        logger.info("game stream started game_id=%s phase=%s round=%s", game_id, session["phase"], session["round"])
        for updated_session, event in self.executor.iter_game_events(session):
            session = updated_session
            await self._persist_session_state(session)
            await self._append_persisted_event(session, event)
            yield session, event

        latest_session = await self.session_store.get_session(game_id)
        if latest_session is not None:
            session = self._runtime_session_from_snapshot(latest_session)
        await self._persist_session_state(session)
        logger.info("game stream finished game_id=%s status=%s winner=%s", game_id, session["status"], session["winner"])

    async def _run_game_stream(self, game_id: str, send_event: EventSender) -> None:
        try:
            async for updated_session, event in self.stream_game_events(game_id):
                await send_event(event)
        except asyncio.CancelledError:
            logger.info("game stream task cancelled game_id=%s", game_id)
            raise
        except Exception:
            logger.exception("game stream task failed game_id=%s", game_id)
            raise
        finally:
            if self._active_game_id == game_id:
                self._active_run_task = None

    async def start_game_stream(self, game_id: str, send_event: EventSender) -> None:
        await self._cancel_active_run_task()
        stored_session = await self.session_store.get_session(game_id)
        if stored_session is not None and stored_session.get("started_at") is None:
            stored_session["started_at"] = _timestamp()
            await self.session_store.update_session(game_id, stored_session)
        self._active_run_task = asyncio.create_task(self._run_game_stream(game_id, send_event))

    async def handle_pause(self, game_id: str) -> dict[str, Any]:
        session = await self.session_store.get_session(game_id)
        if session is None:
            return {"event": "ERROR", "message": f"game_id {game_id} not found"}
        session = self.state_machine.pause_game(session)
        logger.info("game paused game_id=%s phase=%s", game_id, session["phase"])
        await self.session_store.update_session(game_id, session)
        await self._cancel_active_run_task()
        return {"event": "GAME_PAUSED", "game_id": game_id, "status": session["status"], "phase": session["phase"]}

    async def handle_reset(self, game_id: str | None = None) -> dict[str, Any]:
        target_game_id = game_id or self._active_game_id
        if target_game_id is not None:
            logger.info("game reset game_id=%s", target_game_id)
            await self._cancel_active_run_task()
            await self._archive_game_state(target_game_id)
            return build_game_reset_event(target_game_id)

        logger.info("game reset without active game_id")
        return build_game_reset_event()

    async def handle_stop(self, game_id: str) -> dict[str, Any]:
        stored_session = await self.session_store.get_session(game_id)
        if stored_session is None:
            return {"event": "ERROR", "message": f"game_id {game_id} not found"}

        session = self._runtime_session_from_snapshot(stored_session)
        session = self.state_machine.finish_game(session, winner="stopped")
        logger.info("game stopped game_id=%s", game_id)
        await self._persist_session_state(session)
        game_over_event = build_game_over_event(session)
        await self._append_persisted_event(session, game_over_event)
        await self._cancel_active_run_task()
        await self._archive_game_state(game_id)
        return game_over_event
