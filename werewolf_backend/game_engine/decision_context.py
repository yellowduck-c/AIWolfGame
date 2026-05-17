from __future__ import annotations

from collections import Counter
from typing import Literal

from agent.roles.base_agent import BaseAgent
from agent.state.schemas import AgentDecisionInput
from game_engine.models import AgentSnapshot, GameSession


ROLE_SKILLS: dict[str, str] = {
    "狼人": "kill",
    "预言家": "inspect",
    "女巫": "brew",
    "猎人": "shoot",
}


WITCH_HEAL_FACT_TYPE = "witch_heal_used"
WITCH_POISON_FACT_TYPE = "witch_poison_used"
SEER_INSPECTION_FACT_TYPE = "seer_inspection"
HUNTER_SHOT_FACT_TYPE = "hunter_shot_used"

ContextVisibility = Literal["private", "public_only"]


def _alive_agents(session: GameSession) -> list[AgentSnapshot]:
    return [agent for agent in session["agents"] if agent["status"] == "alive"]


def _has_private_fact(agent: BaseAgent, fact_type: str) -> bool:
    return any(fact.get("type") == fact_type for fact in agent.memory.private_facts)


def _build_public_state(session: GameSession) -> dict[str, object]:
    return {
        "phase": session["phase"],
        "round": session["round"],
        "alive_agents": [
            {
                "id": agent["id"],
                "status": agent["status"],
            }
            for agent in _alive_agents(session)
        ],
        "public_events": session["public_events"],
    }


def _build_private_state(
    session: GameSession,
    agent_snapshot: AgentSnapshot,
    agent: BaseAgent,
    *,
    visibility: ContextVisibility,
) -> dict[str, object]:
    private_state: dict[str, object] = {
        "self": {
            "id": agent_snapshot["id"],
            "role": agent_snapshot["role"],
            "camp": agent_snapshot["camp"],
            "status": agent_snapshot["status"],
        },
        "private_facts": [] if visibility == "public_only" else agent.memory.private_facts,
    }
    if visibility == "public_only":
        return private_state
    if agent_snapshot["role"] in ROLE_SKILLS:
        private_state["skill"] = ROLE_SKILLS[agent_snapshot["role"]]
    if agent_snapshot["role"] == "女巫":
        private_state["witch_resources"] = {
            "heal_available": not _has_private_fact(agent, WITCH_HEAL_FACT_TYPE),
            "poison_available": not _has_private_fact(agent, WITCH_POISON_FACT_TYPE),
        }
        private_state["night_context"] = {
            "wolf_target_id": session.get("night_pending_target_id"),
        }
    return private_state


def _build_camp_shared_state(
    session: GameSession,
    agent_snapshot: AgentSnapshot,
    agent: BaseAgent | None = None,
    *,
    visibility: ContextVisibility = "private",
) -> dict[str, object]:
    if agent_snapshot["camp"] != "狼人":
        return {}
    teammates = [
        {"id": other_agent["id"]}
        for other_agent in _alive_agents(session)
        if other_agent["camp"] == agent_snapshot["camp"] and other_agent["id"] != agent_snapshot["id"]
    ]
    camp_chat_history: list[dict[str, object]] = []
    if agent is not None and visibility == "private":
        camp_chat_history = [
            {
                "round": fact.get("round"),
                "from_id": fact.get("from_id"),
                "content": fact.get("content"),
            }
            for fact in agent.memory.private_facts
            if fact.get("type") == "camp_chat_observed"
        ]
    return {
        "teammates": teammates,
        "camp_chat_history": camp_chat_history,
    }


def _summarize_recent_key_events(session: GameSession, *, limit: int = 5) -> list[dict[str, object]]:
    key_events = [
        event
        for event in session["public_events"]
        if event.get("event") in {"PHASE_CHANGE", "AGENT_STATUS_CHANGE", "AGENT_VOTE", "AGENT_SKILL", "GAME_OVER"}
    ]
    return [
        {
            "event": event.get("event"),
            "round": event.get("round"),
            "phase": event.get("phase"),
            "agent_id": event.get("agent_id"),
            "target_id": event.get("target_id"),
            "status": event.get("status"),
            "cause": event.get("cause"),
        }
        for event in key_events[-limit:]
    ]


def _extract_consensus_target(camp_chat_history: list[dict[str, object]], legal_targets: list[int]) -> tuple[int | None, float, str | None]:
    mentions: list[int] = []
    latest_reason: str | None = None
    for entry in camp_chat_history:
        content = str(entry.get("content") or "")
        latest_reason = content or latest_reason
        for target_id in legal_targets:
            if f"{target_id}号" in content or f"{target_id} 号" in content:
                mentions.append(target_id)
    if not mentions:
        return None, 0.0, latest_reason
    counter = Counter(mentions)
    target_id, count = counter.most_common(1)[0]
    confidence = round(count / len(mentions), 2) if mentions else 0.0
    return target_id, confidence, latest_reason


def _build_derived_context(
    session: GameSession,
    agent_snapshot: AgentSnapshot,
    agent: BaseAgent,
    camp_shared_state: dict[str, object],
    legal_actions: dict[str, object],
    *,
    visibility: ContextVisibility,
) -> dict[str, object]:
    derived_context: dict[str, object] = {
        "recent_key_events": _summarize_recent_key_events(session),
        "alive_player_ids": [candidate["id"] for candidate in _alive_agents(session)],
    }

    if visibility == "public_only":
        if legal_actions.get("type") == "vote":
            derived_context["vote_action_summary"] = {
                "candidates": legal_actions.get("candidates", []),
            }
        return derived_context

    if agent_snapshot["camp"] == "狼人":
        camp_chat_history = camp_shared_state.get("camp_chat_history", [])
        if isinstance(camp_chat_history, list):
            recent_chat = camp_chat_history[-3:]
            derived_context["recent_camp_chat_summary"] = [
                {
                    "round": entry.get("round"),
                    "from_id": entry.get("from_id"),
                    "content": entry.get("content"),
                }
                for entry in recent_chat
            ]
            consensus_target_id, consensus_confidence, latest_reason = _extract_consensus_target(
                camp_chat_history,
                [target_id for target_id in legal_actions.get("targets", []) if isinstance(target_id, int)],
            )
            derived_context["consensus_target_id"] = consensus_target_id
            derived_context["consensus_confidence"] = consensus_confidence
            derived_context["latest_consensus_reason"] = latest_reason

    if agent_snapshot["role"] == "女巫":
        derived_context["witch_action_summary"] = {
            "wolf_target_id": legal_actions.get("wolf_target_id"),
            "can_heal": legal_actions.get("can_heal"),
            "can_poison": legal_actions.get("can_poison"),
        }
    elif agent_snapshot["role"] == "预言家":
        derived_context["seer_action_summary"] = {
            "available_targets": legal_actions.get("targets", []),
        }
    elif agent_snapshot["role"] == "猎人":
        derived_context["hunter_action_summary"] = {
            "triggered_by_death": legal_actions.get("triggered_by_death"),
            "death_cause": legal_actions.get("death_cause"),
            "available_targets": legal_actions.get("targets", []),
        }

    if legal_actions.get("type") == "vote":
        derived_context["vote_action_summary"] = {
            "candidates": legal_actions.get("candidates", []),
        }
    elif legal_actions.get("type") == "skill":
        derived_context["skill_action_summary"] = {
            "skill": legal_actions.get("skill"),
            "targets": legal_actions.get("targets", []),
            "allowed": legal_actions.get("allowed"),
        }
    elif legal_actions.get("type") == "camp_chat":
        derived_context["camp_chat_action_summary"] = {
            "audience": legal_actions.get("audience", []),
        }

    return derived_context


def build_vote_legal_actions(session: GameSession, agent_snapshot: AgentSnapshot) -> dict[str, object]:
    return {
        "type": "vote",
        "candidates": [
            candidate["id"]
            for candidate in _alive_agents(session)
            if candidate["id"] != agent_snapshot["id"]
        ],
    }


def build_skill_legal_actions(session: GameSession, agent_snapshot: AgentSnapshot, agent: BaseAgent | None = None) -> dict[str, object]:
    allowed = agent_snapshot["role"] in ROLE_SKILLS
    targets = [
        candidate["id"]
        for candidate in _alive_agents(session)
        if candidate["id"] != agent_snapshot["id"]
        and not (agent_snapshot["role"] == "狼人" and candidate["camp"] == "狼人")
    ]
    legal_actions: dict[str, object] = {
        "type": "skill",
        "allowed": allowed,
        "skill": ROLE_SKILLS.get(agent_snapshot["role"]),
        "targets": targets,
    }
    if agent_snapshot["role"] == "女巫" and agent is not None:
        heal_available = not _has_private_fact(agent, WITCH_HEAL_FACT_TYPE)
        poison_available = not _has_private_fact(agent, WITCH_POISON_FACT_TYPE)
        wolf_target_id = session.get("night_pending_target_id")
        potion_used_tonight = session.get("witch_potion_used") is True
        legal_actions["heal_available"] = heal_available
        legal_actions["poison_available"] = poison_available
        legal_actions["wolf_target_id"] = wolf_target_id
        legal_actions["can_heal"] = heal_available and wolf_target_id is not None and not potion_used_tonight
        legal_actions["can_poison"] = poison_available and not potion_used_tonight
        legal_actions["potion_used_tonight"] = potion_used_tonight
        legal_actions["allowed"] = not potion_used_tonight and (
            legal_actions["can_heal"] or legal_actions["can_poison"]
        )
    if agent_snapshot["role"] == "猎人" and agent is not None:
        legal_actions["triggered_by_death"] = session.get("hunter_pending_shot_id") == agent_snapshot["id"]
        legal_actions["death_cause"] = session.get("hunter_pending_shot_cause")
        legal_actions["allowed"] = (
            bool(legal_actions["triggered_by_death"])
            and legal_actions["death_cause"] in {"wolf_attack", "vote_exile"}
            and not _has_private_fact(agent, HUNTER_SHOT_FACT_TYPE)
        )
        legal_actions["targets"] = [
            candidate["id"]
            for candidate in _alive_agents(session)
            if candidate["id"] != agent_snapshot["id"]
        ]
    return legal_actions


def build_agent_decision_input(
    session: GameSession,
    agent_snapshot: AgentSnapshot,
    agent: BaseAgent,
    legal_actions: dict[str, object],
    *,
    visibility: ContextVisibility = "private",
) -> AgentDecisionInput:
    camp_shared_state = _build_camp_shared_state(session, agent_snapshot, agent, visibility=visibility)
    include_private_facts = visibility == "private"
    return AgentDecisionInput(
        agent_id=agent_snapshot["id"],
        role=agent_snapshot["role"],
        camp=agent_snapshot["camp"],
        phase=session["phase"],
        round=session["round"],
        public_state=_build_public_state(session),
        private_state=_build_private_state(session, agent_snapshot, agent, visibility=visibility),
        camp_shared_state=camp_shared_state,
        memory_summary=agent.memory.to_summary(include_private_facts=include_private_facts),
        legal_actions=legal_actions,
        derived_context=_build_derived_context(
            session,
            agent_snapshot,
            agent,
            camp_shared_state,
            legal_actions,
            visibility=visibility,
        ),
    )
