from __future__ import annotations

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


def _build_private_state(session: GameSession, agent_snapshot: AgentSnapshot, agent: BaseAgent) -> dict[str, object]:
    private_state: dict[str, object] = {
        "self": {
            "id": agent_snapshot["id"],
            "role": agent_snapshot["role"],
            "camp": agent_snapshot["camp"],
            "status": agent_snapshot["status"],
        },
        "private_facts": agent.memory.private_facts,
    }
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


def _build_camp_shared_state(session: GameSession, agent_snapshot: AgentSnapshot) -> dict[str, object]:
    if agent_snapshot["camp"] != "狼人":
        return {}
    return {
        "teammates": [
            {"id": agent["id"], "role": agent["role"]}
            for agent in _alive_agents(session)
            if agent["camp"] == agent_snapshot["camp"] and agent["id"] != agent_snapshot["id"]
        ]
    }


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
        legal_actions["targets"] = [
            target_id for target_id in legal_actions["targets"] if target_id != agent_snapshot["id"]
        ]
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
) -> AgentDecisionInput:
    return AgentDecisionInput(
        agent_id=agent_snapshot["id"],
        role=agent_snapshot["role"],
        camp=agent_snapshot["camp"],
        phase=session["phase"],
        round=session["round"],
        public_state=_build_public_state(session),
        private_state=_build_private_state(session, agent_snapshot, agent),
        camp_shared_state=_build_camp_shared_state(session, agent_snapshot),
        memory_summary=agent.memory.to_summary(),
        legal_actions=legal_actions,
    )
