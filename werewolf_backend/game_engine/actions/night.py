from __future__ import annotations

import logging
import random
from collections import Counter
from collections.abc import Iterator
from typing import Any

from agent.core.registry import agent_registry
from game_engine.decision_context import (
    HUNTER_SHOT_FACT_TYPE,
    SEER_INSPECTION_FACT_TYPE,
    WITCH_HEAL_FACT_TYPE,
    WITCH_POISON_FACT_TYPE,
    build_agent_decision_input,
    build_skill_legal_actions,
)
from game_engine.events import (
    PRIVATE_EVENT_TYPES,
    build_camp_chat_event,
    build_game_over_event,
    build_phase_change_event,
    build_skill_event,
    build_status_change_event,
)
from game_engine.models import GamePhase, GameSession
from game_engine.state_machine import GameStateMachine

logger = logging.getLogger(__name__)

NIGHT_ACTION_ORDER: tuple[str, ...] = ("狼人", "预言家", "女巫")
NIGHT_ACTIVE_ROLES: frozenset[str] = frozenset(NIGHT_ACTION_ORDER)


def _resolve_wolf_target(wolf_votes: list[int]) -> int | None:
    if not wolf_votes:
        return None
    vote_counter = Counter(wolf_votes)
    top_vote_count = max(vote_counter.values())
    top_targets = [target_id for target_id, count in vote_counter.items() if count == top_vote_count]
    if len(top_targets) == 1:
        return top_targets[0]
    return random.choice(top_targets)


def stream_night_action(
    session: GameSession,
    state_machine: GameStateMachine,
) -> Iterator[tuple[GameSession, dict[str, Any]]]:
    session["phase"] = GamePhase.NIGHT
    logger.info("night phase started game_id=%s round=%s", session["game_id"], session["round"])
    yield session, build_phase_change_event(session)

    wolf_target_id: int | None = None
    wolf_votes: list[int] = []
    witch_heal_used = False
    witch_poison_target_id: int | None = None
    session.pop("witch_potion_used", None)

    def emit_visible_event(event: dict[str, Any]) -> tuple[GameSession, dict[str, Any]]:
        if event.get("event") not in PRIVATE_EVENT_TYPES:
            session["public_events"].append(event)
        return session, event

    def emit_death(agent_id: int, *, cause: str) -> Iterator[tuple[GameSession, dict[str, Any]]]:
        nonlocal session
        session = state_machine.mark_agent_dead(session, agent_id=agent_id)
        logger.info("agent status changed game_id=%s round=%s agent_id=%s status=dead cause=%s", session["game_id"], session["round"], agent_id, cause)
        status_event = build_status_change_event(agent_id=agent_id, status="dead", cause=cause)
        session["public_events"].append(status_event)
        for public_agent_snapshot in session["agents"]:
            public_agent = agent_registry.get_agent(session["game_id"], public_agent_snapshot["id"])
            public_agent.observe_public_event(status_event)
        yield session, status_event

    def resolve_hunter_shot(agent_id: int, *, cause: str) -> Iterator[tuple[GameSession, dict[str, Any]]]:
        hunter_snapshot = next(agent for agent in session["agents"] if agent["id"] == agent_id)
        hunter_agent = agent_registry.get_agent(session["game_id"], agent_id)
        session["hunter_pending_shot_id"] = agent_id
        session["hunter_pending_shot_cause"] = cause
        legal_actions = build_skill_legal_actions(session, hunter_snapshot, hunter_agent)
        decision_input = build_agent_decision_input(session, hunter_snapshot, hunter_agent, legal_actions=legal_actions)
        if not decision_input.legal_actions["allowed"]:
            session.pop("hunter_pending_shot_id", None)
            session.pop("hunter_pending_shot_cause", None)
            return

        decision = hunter_agent.use_skill(decision_input)
        logger.info("hunter shot game_id=%s round=%s agent_id=%s target_id=%s", session["game_id"], session["round"], hunter_snapshot["id"], decision.target_id)
        if decision.target_id is None or decision.target_id not in legal_actions["targets"]:
            session.pop("hunter_pending_shot_id", None)
            session.pop("hunter_pending_shot_cause", None)
            return
        hunter_agent.observe_private_fact({"type": HUNTER_SHOT_FACT_TYPE, "round": session["round"], "target_id": decision.target_id})
        shot_event = build_skill_event(
            agent_id=hunter_snapshot["id"],
            role=hunter_snapshot["role"],
            skill=decision.skill,
            target_id=decision.target_id,
        )
        if shot_event.get("event") not in PRIVATE_EVENT_TYPES:
            session["public_events"].append(shot_event)
        yield session, shot_event
        yield from emit_death(decision.target_id, cause="hunter_shot")
        session.pop("hunter_pending_shot_id", None)
        session.pop("hunter_pending_shot_cause", None)

    ordered_active_agents = [
        agent_snapshot
        for role in NIGHT_ACTION_ORDER
        for agent_snapshot in session["agents"]
        if agent_snapshot["status"] == "alive" and agent_snapshot["role"] == role
    ]
    last_wolf_agent_id = next(
        (agent_snapshot["id"] for agent_snapshot in reversed(ordered_active_agents) if agent_snapshot["role"] == "狼人"),
        None,
    )

    # Wolf camp private chat round (not public)
    alive_wolves = [a for a in session["agents"] if a["status"] == "alive" and a["role"] == "狼人"]
    if alive_wolves:
        teammate_ids = [a["id"] for a in alive_wolves]
        logger.info(
            "wolf camp chat phase started game_id=%s round=%s alive_wolf_ids=%s",
            session["game_id"],
            session["round"],
            teammate_ids,
        )
        for agent_snapshot in alive_wolves:
            agent = agent_registry.get_agent(session["game_id"], agent_snapshot["id"])
            legal_actions = {"type": "camp_chat", "allowed": len(teammate_ids) > 1, "audience": [i for i in teammate_ids if i != agent_snapshot["id"]]}
            decision_input = build_agent_decision_input(session, agent_snapshot, agent, legal_actions=legal_actions)
            if not legal_actions["allowed"]:
                logger.info(
                    "wolf camp chat skipped game_id=%s round=%s agent_id=%s reason=no_teammate",
                    session["game_id"],
                    session["round"],
                    agent_snapshot["id"],
                )
                continue
            chat_func = getattr(agent, "camp_chat", None)
            if not callable(chat_func):
                logger.info(
                    "wolf camp chat skipped game_id=%s round=%s agent_id=%s reason=missing_callable",
                    session["game_id"],
                    session["round"],
                    agent_snapshot["id"],
                )
                continue
            logger.info(
                "wolf camp chat attempt game_id=%s round=%s agent_id=%s audience=%s",
                session["game_id"],
                session["round"],
                agent_snapshot["id"],
                legal_actions["audience"],
            )
            content = chat_func(decision_input)
            if content:
                logger.info(
                    "wolf camp chat generated game_id=%s round=%s agent_id=%s content_chars=%s",
                    session["game_id"],
                    session["round"],
                    agent_snapshot["id"],
                    len(content),
                )
                session.setdefault("camp_private_logs", {}).setdefault("狼人", []).append({
                    "round": session["round"],
                    "from_id": agent_snapshot["id"],
                    "content": content,
                })

                # Spectator-visible only: emit to stream without writing into public_events
                yield session, build_camp_chat_event(camp="狼人", from_id=agent_snapshot["id"], content=content)

                for teammate in alive_wolves:
                    teammate_agent = agent_registry.get_agent(session["game_id"], teammate["id"])
                    teammate_agent.observe_private_fact({
                        "type": "camp_chat_observed",
                        "round": session["round"],
                        "from_id": agent_snapshot["id"],
                        "content": content,
                    })
            else:
                logger.info(
                    "wolf camp chat empty game_id=%s round=%s agent_id=%s",
                    session["game_id"],
                    session["round"],
                    agent_snapshot["id"],
                )

    for agent_snapshot in ordered_active_agents:
        agent = agent_registry.get_agent(session["game_id"], agent_snapshot["id"])

        if agent_snapshot["role"] == "狼人":
            legal_actions = build_skill_legal_actions(session, agent_snapshot, agent)
            decision_input = build_agent_decision_input(session, agent_snapshot, agent, legal_actions=legal_actions)
            if not decision_input.legal_actions["allowed"]:
                continue
            camp_chat_history = decision_input.camp_shared_state.get("camp_chat_history", [])
            logger.info(
                "wolf kill decision context game_id=%s round=%s agent_id=%s chat_history_count=%s latest_chat=%s",
                session["game_id"],
                session["round"],
                agent_snapshot["id"],
                len(camp_chat_history),
                camp_chat_history[-1] if camp_chat_history else None,
            )
            decision = agent.use_skill(decision_input)
            logger.info("night action game_id=%s round=%s agent_id=%s role=%s skill=%s target_id=%s", session["game_id"], session["round"], agent_snapshot["id"], agent_snapshot["role"], decision.skill, decision.target_id)
            skill_event = build_skill_event(
                agent_id=agent_snapshot["id"],
                role=agent_snapshot["role"],
                skill=decision.skill,
                target_id=decision.target_id,
            )
            if decision.target_id is not None:
                wolf_votes.append(decision.target_id)
            yield emit_visible_event(skill_event)
            if agent_snapshot["id"] == last_wolf_agent_id:
                wolf_target_id = _resolve_wolf_target(wolf_votes)
                if wolf_target_id is not None:
                    session["night_pending_target_id"] = wolf_target_id
            continue

        if agent_snapshot["role"] == "预言家":
            legal_actions = build_skill_legal_actions(session, agent_snapshot, agent)
            decision_input = build_agent_decision_input(session, agent_snapshot, agent, legal_actions=legal_actions)
            if not decision_input.legal_actions["allowed"]:
                continue
            decision = agent.use_skill(decision_input)
            logger.info("night action game_id=%s round=%s agent_id=%s role=%s skill=%s target_id=%s", session["game_id"], session["round"], agent_snapshot["id"], agent_snapshot["role"], decision.skill, decision.target_id)
            skill_event = build_skill_event(
                agent_id=agent_snapshot["id"],
                role=agent_snapshot["role"],
                skill=decision.skill,
                target_id=decision.target_id,
            )
            if decision.target_id is not None:
                inspected_snapshot = next(candidate for candidate in session["agents"] if candidate["id"] == decision.target_id)
                agent.observe_private_fact(
                    {
                        "type": SEER_INSPECTION_FACT_TYPE,
                        "round": session["round"],
                        "target_id": inspected_snapshot["id"],
                        "role": inspected_snapshot["role"],
                        "camp": inspected_snapshot["camp"],
                    }
                )
            yield emit_visible_event(skill_event)
            continue

        legal_actions = build_skill_legal_actions(session, agent_snapshot, agent)
        decision_input = build_agent_decision_input(session, agent_snapshot, agent, legal_actions=legal_actions)
        witch_resources = decision_input.private_state["witch_resources"]
        logger.info("witch resources game_id=%s round=%s agent_id=%s resources=%s", session["game_id"], session["round"], agent_snapshot["id"], witch_resources)
        decision = agent.use_skill(decision_input)
        logger.info("night action game_id=%s round=%s agent_id=%s role=%s skill=%s target_id=%s", session["game_id"], session["round"], agent_snapshot["id"], agent_snapshot["role"], decision.skill, decision.target_id)
        if decision.skill == "heal" and legal_actions["can_heal"] and legal_actions["wolf_target_id"] is not None:
            witch_heal_used = True
            session["witch_potion_used"] = True
            agent.observe_private_fact({"type": WITCH_HEAL_FACT_TYPE, "round": session["round"]})
            heal_event = build_skill_event(
                agent_id=agent_snapshot["id"],
                role=agent_snapshot["role"],
                skill="heal",
                target_id=legal_actions["wolf_target_id"],
            )
            yield emit_visible_event(heal_event)
            continue

        poison_target_id = decision.target_id if decision.skill == "poison" else None
        if decision.skill == "poison" and legal_actions["can_poison"] and poison_target_id is not None:
            witch_poison_target_id = poison_target_id
            session["witch_potion_used"] = True
            agent.observe_private_fact(
                {
                    "type": WITCH_POISON_FACT_TYPE,
                    "round": session["round"],
                    "target_id": witch_poison_target_id,
                }
            )
        poison_event = build_skill_event(
            agent_id=agent_snapshot["id"],
            role=agent_snapshot["role"],
            skill=decision.skill,
            target_id=poison_target_id,
        )
        yield emit_visible_event(poison_event)

    wolf_target_id = _resolve_wolf_target(wolf_votes)
    if wolf_target_id is not None:
        session["night_pending_target_id"] = wolf_target_id

    eliminated_agent_ids: list[int] = []
    if wolf_target_id is not None and not witch_heal_used:
        eliminated_agent_ids.append(wolf_target_id)
    if witch_poison_target_id is not None and witch_poison_target_id not in eliminated_agent_ids:
        eliminated_agent_ids.append(witch_poison_target_id)

    for eliminated_agent_id in eliminated_agent_ids:
        if next(agent for agent in session["agents"] if agent["id"] == eliminated_agent_id)["status"] != "alive":
            continue
        cause = "poison" if eliminated_agent_id == witch_poison_target_id else "wolf_attack"
        yield from emit_death(eliminated_agent_id, cause=cause)
        eliminated_snapshot = next(agent for agent in session["agents"] if agent["id"] == eliminated_agent_id)
        if eliminated_snapshot["role"] == "猎人" and cause == "wolf_attack":
            yield from resolve_hunter_shot(eliminated_agent_id, cause=cause)

    session.pop("hunter_pending_shot_id", None)
    session.pop("night_pending_target_id", None)
    session.pop("witch_potion_used", None)
    winner = state_machine.calculate_winner(session)
    if winner is not None:
        session = state_machine.finish_game(session, winner=winner)
        logger.info("game finished during night game_id=%s winner=%s round=%s", session["game_id"], winner, session["round"])
        finish_phase_event = build_phase_change_event(session)
        game_over_event = build_game_over_event(session)
        session["public_events"].extend([finish_phase_event, game_over_event])
        yield session, finish_phase_event
        yield session, game_over_event


def run_night_action(
    session: GameSession,
    state_machine: GameStateMachine,
) -> tuple[GameSession, list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    updated_session = session
    for updated_session, event in stream_night_action(session, state_machine):
        events.append(event)
    return updated_session, events
