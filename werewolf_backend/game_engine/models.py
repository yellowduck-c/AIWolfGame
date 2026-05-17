from __future__ import annotations

from enum import Enum
from typing import Literal, TypedDict


class AgentStatus(str, Enum):
    ALIVE = "alive"
    DEAD = "dead"
    EXILED = "exiled"


class GamePhase(str, Enum):
    NIGHT = "night"
    DAY_SPEECH = "day_speech"
    VOTING = "voting"
    FINISHED = "finished"


class GameStatus(str, Enum):
    RUNNING = "running"
    PAUSED = "paused"
    FINISHED = "finished"


class AgentSnapshot(TypedDict):
    id: int
    role: str
    camp: str
    status: Literal["alive", "dead", "exiled"]


class GameSession(TypedDict):
    game_id: str
    phase: Literal["night", "day_speech", "voting", "finished"]
    round: int
    status: Literal["running", "paused", "finished"]
    agents: list[AgentSnapshot]
    winner: str | None
    public_events: list[dict[str, object]]
