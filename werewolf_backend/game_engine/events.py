from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from game_engine.models import GameSession


PRIVATE_EVENT_TYPES = frozenset({"AGENT_SKILL", "CAMP_CHAT"})


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def enrich_persisted_event(session: GameSession, event: dict[str, Any]) -> dict[str, Any]:
    return {
        **event,
        "game_id": session["game_id"],
        "phase": session["phase"],
        "round": session["round"],
        "timestamp": _timestamp(),
    }


def build_phase_change_event(session: GameSession) -> dict[str, Any]:
    return {"event": "PHASE_CHANGE", "phase": session["phase"], "round": session["round"]}


def build_game_over_event(session: GameSession) -> dict[str, Any]:
    return {"event": "GAME_OVER", "winner": session["winner"] or "unknown", "game_id": session["game_id"]}


def build_status_change_event(agent_id: int, status: str, **payload: Any) -> dict[str, Any]:
    return {"event": "AGENT_STATUS_CHANGE", "id": agent_id, "status": status, **payload}


def build_public_status_change_event(agent_id: int, status: str, **payload: Any) -> dict[str, Any]:
    sanitized_payload = {key: value for key, value in payload.items() if key not in {"role", "revealed_role"}}
    return {"event": "AGENT_STATUS_CHANGE", "id": agent_id, "status": status, **sanitized_payload}


def build_speak_event(agent_id: int, role: str, content: str) -> dict[str, Any]:
    return {
        "event": "AGENT_SPEAK",
        "id": agent_id,
        "content": content,
        "role": role,
    }


def build_public_speak_event(agent_id: int, content: str) -> dict[str, Any]:
    return {
        "event": "AGENT_SPEAK",
        "id": agent_id,
        "content": content,
    }


def build_speak_chunk_event(agent_id: int, role: str, content: str) -> dict[str, Any]:
    return {
        "event": "AGENT_SPEAK_CHUNK",
        "id": agent_id,
        "content": content,
        "role": role,
    }


def build_public_speak_chunk_event(agent_id: int, content: str) -> dict[str, Any]:
    return {
        "event": "AGENT_SPEAK_CHUNK",
        "id": agent_id,
        "content": content,
    }


def build_vote_event(agent_id: int, target_id: int) -> dict[str, Any]:
    return {"event": "AGENT_VOTE", "id": agent_id, "target_id": target_id}


def build_skill_event(agent_id: int, role: str, skill: str, target_id: int | None) -> dict[str, Any]:
    return {
        "event": "AGENT_SKILL",
        "id": agent_id,
        "role": role,
        "skill": skill,
        "target_id": target_id,
    }


def build_camp_chat_event(*, camp: str, from_id: int, content: str) -> dict[str, Any]:
    return {
        "event": "CAMP_CHAT",
        "camp": camp,
        "from_id": from_id,
        "content": content,
    }
