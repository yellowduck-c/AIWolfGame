from __future__ import annotations

from agent.roles.base_agent import BaseAgent


class AgentRegistry:
    def __init__(self) -> None:
        self._agents_by_game: dict[str, dict[int, BaseAgent]] = {}

    def register_game_agents(self, game_id: str, agents_by_player_id: dict[int, BaseAgent]) -> None:
        self._agents_by_game[game_id] = agents_by_player_id

    def get_agent(self, game_id: str, player_id: int) -> BaseAgent:
        return self._agents_by_game[game_id][player_id]

    def clear_game(self, game_id: str) -> None:
        self._agents_by_game.pop(game_id, None)


agent_registry = AgentRegistry()
