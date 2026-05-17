from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AgentDecisionInput:
    agent_id: int
    role: str
    camp: str
    phase: str
    round: int
    public_state: dict[str, Any]
    private_state: dict[str, Any]
    camp_shared_state: dict[str, Any]
    memory_summary: dict[str, Any]
    legal_actions: dict[str, Any]
    derived_context: dict[str, Any] = field(default_factory=dict)
    specialization: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SpeechDecision:
    content: str


@dataclass(slots=True)
class StreamingSpeechDecision:
    content: str
    chunks: list[str]


@dataclass(slots=True)
class VoteDecision:
    target_id: int


@dataclass(slots=True)
class SkillDecision:
    skill: str
    target_id: int | None


@dataclass(slots=True)
class SkillResolution:
    actor_id: int
    role: str
    skill: str
    target_id: int | None
