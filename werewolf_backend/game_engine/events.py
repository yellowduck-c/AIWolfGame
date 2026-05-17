from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from game_engine.models import GameSession



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



def build_speak_event(agent_id: int, role: str, content: str) -> dict[str, Any]:
    return {
        "event": "AGENT_SPEAK",
        "id": agent_id,
        "role": role,
        "content": content,
    }



def build_speak_chunk_event(agent_id: int, role: str, content: str) -> dict[str, Any]:
    return {
        "event": "AGENT_SPEAK_CHUNK",
        "id": agent_id,
        "role": role,
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
