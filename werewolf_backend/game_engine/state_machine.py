from __future__ import annotations

from typing import Any

from game_engine.models import GamePhase, GameSession, GameStatus

PHASE_ORDER = [GamePhase.NIGHT, GamePhase.DAY_SPEECH, GamePhase.VOTING]


class GameStateMachine:
    def create_initial_session(self, game_id: str, agents: list[dict[str, Any]]) -> GameSession:
        return {
            "game_id": game_id,
            "phase": GamePhase.NIGHT,
            "round": 1,
            "status": GameStatus.RUNNING,
            "agents": agents,
            "winner": None,
            "public_events": [],
        }

    def advance_phase(self, session: GameSession) -> GameSession:
        if session["status"] == GameStatus.FINISHED or session["phase"] == GamePhase.FINISHED:
            return session

        current_phase = GamePhase(session["phase"])
        if current_phase == GamePhase.VOTING:
            session["phase"] = GamePhase.NIGHT
            session["round"] += 1
            return session

        current_index = PHASE_ORDER.index(current_phase)
        next_phase = PHASE_ORDER[current_index + 1]
        session["phase"] = next_phase
        return session

    def mark_agent_dead(self, session: GameSession, agent_id: int) -> GameSession:
        for agent in session["agents"]:
            if agent["id"] == agent_id:
                agent["status"] = "dead"
                break
        return session

    def mark_agent_exiled(self, session: GameSession, agent_id: int) -> GameSession:
        for agent in session["agents"]:
            if agent["id"] == agent_id:
                agent["status"] = "exiled"
                break
        return session

    def is_agent_active(self, agent: dict[str, Any]) -> bool:
        status = agent["status"]
        role = agent["role"]
        return status == "alive" or (role == "白痴" and status == "exiled")

    def calculate_winner(self, session: GameSession) -> str | None:
        active_agents = [agent for agent in session["agents"] if self.is_agent_active(agent)]
        active_wolves = [agent for agent in active_agents if agent["camp"] == "狼人"]
        active_non_wolves = [agent for agent in active_agents if agent["camp"] != "狼人"]

        if not active_wolves:
            return "好人"
        if len(active_wolves) >= len(active_non_wolves):
            return "狼人"
        return None

    def finish_game(self, session: GameSession, winner: str) -> GameSession:
        session["phase"] = GamePhase.FINISHED
        session["status"] = GameStatus.FINISHED
        session["winner"] = winner
        return session

    def pause_game(self, session: GameSession) -> GameSession:
        session["status"] = GameStatus.PAUSED
        return session
