from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _copy_event_list(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [dict(event) for event in events]


@dataclass(slots=True)
class AgentIdentityMemory:
    player_id: int
    role: str
    camp: str


@dataclass(slots=True)
class AgentDecisionHistory:
    speeches: list[str] = field(default_factory=list)
    votes: list[int] = field(default_factory=list)
    skills: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class AgentMemory:
    identity: AgentIdentityMemory
    public_observations: list[dict[str, Any]] = field(default_factory=list)
    private_facts: list[dict[str, Any]] = field(default_factory=list)
    decision_history: AgentDecisionHistory = field(default_factory=AgentDecisionHistory)

    def record_public_observation(self, event: dict[str, Any]) -> None:
        self.public_observations.append(event)

    def record_private_fact(self, fact: dict[str, Any]) -> None:
        self.private_facts.append(fact)

    def record_speech(self, content: str) -> None:
        self.decision_history.speeches.append(content)

    def record_vote(self, target_id: int) -> None:
        self.decision_history.votes.append(target_id)

    def record_skill(self, payload: dict[str, Any]) -> None:
        self.decision_history.skills.append(payload)

    def to_summary(self, *, include_private_facts: bool = True) -> dict[str, Any]:
        return {
            "identity": {
                "player_id": self.identity.player_id,
                "role": self.identity.role,
                "camp": self.identity.camp,
            },
            "public_observations": _copy_event_list(self.public_observations),
            "private_facts": _copy_event_list(self.private_facts) if include_private_facts else [],
            "decision_history": {
                "speeches": list(self.decision_history.speeches),
                "votes": list(self.decision_history.votes),
                "skills": _copy_event_list(self.decision_history.skills),
            },
        }
