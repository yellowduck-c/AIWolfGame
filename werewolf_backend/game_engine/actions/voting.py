from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Iterator

from agent.core.registry import agent_registry
from game_engine.decision_context import HUNTER_SHOT_FACT_TYPE, build_agent_decision_input, build_skill_legal_actions, build_vote_legal_actions
from game_engine.events import PRIVATE_EVENT_TYPES, build_game_over_event, build_phase_change_event, build_public_status_change_event, build_skill_event, build_status_change_event, build_vote_event
from game_engine.models import GameSession
from game_engine.state_machine import GameStateMachine

logger = logging.getLogger(__name__)


def stream_voting_action(
    session: GameSession,
    state_machine: GameStateMachine,
) -> Iterator[tuple[GameSession, dict[str, object]]]:
    logger.info("voting phase started game_id=%s round=%s", session["game_id"], session["round"])
    yield session, build_phase_change_event(session)

    votes: list[int] = []

    def emit(event: dict[str, object], public: bool = False) -> tuple[GameSession, dict[str, object]]:
        if public:
            session["public_events"].append(event)
        return session, event

    def emit_death(agent_id: int) -> Iterator[tuple[GameSession, dict[str, object]]]:
        nonlocal session
        session = state_machine.mark_agent_dead(session, agent_id=agent_id)
        logger.info("agent status changed game_id=%s round=%s agent_id=%s status=dead cause=vote_exile", session["game_id"], session["round"], agent_id)
        status_event = build_status_change_event(agent_id=agent_id, status="dead", cause="vote_exile")
        session["public_events"].append(status_event)
        for agent_snapshot in session["agents"]:
            agent = agent_registry.get_agent(session["game_id"], agent_snapshot["id"])
            agent.observe_public_event(status_event)
        yield session, status_event

    def emit_idiot_exile(agent_id: int) -> Iterator[tuple[GameSession, dict[str, object]]]:
        nonlocal session
        session = state_machine.mark_agent_exiled(session, agent_id=agent_id)
        logger.info("idiot exiled game_id=%s round=%s agent_id=%s status=exiled", session["game_id"], session["round"], agent_id)
        status_event = build_status_change_event(
            agent_id=agent_id,
            status="exiled",
            role="白痴",
            revealed_role="白痴",
            can_vote=False,
            can_speak=False,
            is_alive=True,
            special="idiot_revealed",
        )
        public_status_event = build_public_status_change_event(
            agent_id=agent_id,
            status="exiled",
            role="白痴",
            revealed_role="白痴",
            can_vote=False,
            can_speak=False,
            is_alive=True,
            special="idiot_revealed",
        )
        session["public_events"].append(public_status_event)
        for agent_snapshot in session["agents"]:
            agent = agent_registry.get_agent(session["game_id"], agent_snapshot["id"])
            agent.observe_public_event(public_status_event)
        yield session, status_event

    def resolve_hunter_shot(agent_id: int) -> Iterator[tuple[GameSession, dict[str, object]]]:
        hunter_snapshot = next(agent for agent in session["agents"] if agent["id"] == agent_id)
        hunter_agent = agent_registry.get_agent(session["game_id"], agent_id)
        session["hunter_pending_shot_id"] = agent_id
        session["hunter_pending_shot_cause"] = "vote_exile"
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
        yield from emit_death(decision.target_id)
        session.pop("hunter_pending_shot_id", None)
        session.pop("hunter_pending_shot_cause", None)

    for agent_snapshot in session["agents"]:
        if agent_snapshot["status"] != "alive":
            continue
        agent = agent_registry.get_agent(session["game_id"], agent_snapshot["id"])
        decision_input = build_agent_decision_input(
            session,
            agent_snapshot,
            agent,
            legal_actions=build_vote_legal_actions(session, agent_snapshot),
            visibility="public_only",
        )
        decision = agent.vote(decision_input)
        logger.info("vote cast game_id=%s round=%s agent_id=%s target_id=%s", session["game_id"], session["round"], agent_snapshot["id"], decision.target_id)
        votes.append(decision.target_id)
        vote_event = build_vote_event(agent_id=agent_snapshot["id"], target_id=decision.target_id)
        session["public_events"].append(vote_event)
        yield emit(vote_event)

    if votes:
        vote_counter = Counter(votes)
        top_vote_count = max(vote_counter.values())
        tied_agent_ids = [agent_id for agent_id, count in vote_counter.items() if count == top_vote_count]
        if len(tied_agent_ids) > 1:
            logger.info(
                "vote tied game_id=%s round=%s tied_agent_ids=%s vote_count=%s peaceful_day=true",
                session["game_id"],
                session["round"],
                tied_agent_ids,
                top_vote_count,
            )
            winner = state_machine.calculate_winner(session)
            if winner is not None:
                session = state_machine.finish_game(session, winner=winner)
                logger.info("game finished after tied vote game_id=%s winner=%s round=%s", session["game_id"], winner, session["round"])
                finish_phase_event = build_phase_change_event(session)
                game_over_event = build_game_over_event(session)
                session["public_events"].extend([finish_phase_event, game_over_event])
                yield session, finish_phase_event
                yield session, game_over_event
            return

        eliminated_agent_id = tied_agent_ids[0]
        logger.info("vote resolved game_id=%s round=%s eliminated_agent_id=%s vote_count=%s", session["game_id"], session["round"], eliminated_agent_id, top_vote_count)
        eliminated_snapshot = next(agent for agent in session["agents"] if agent["id"] == eliminated_agent_id)
        if eliminated_snapshot["role"] == "白痴":
            yield from emit_idiot_exile(eliminated_agent_id)
        else:
            yield from emit_death(eliminated_agent_id)
            eliminated_snapshot = next(agent for agent in session["agents"] if agent["id"] == eliminated_agent_id)
            if eliminated_snapshot["role"] == "猎人":
                yield from resolve_hunter_shot(eliminated_agent_id)

        session.pop("hunter_pending_shot_id", None)
        session.pop("hunter_pending_shot_cause", None)
        winner = state_machine.calculate_winner(session)
        if winner is not None:
            session = state_machine.finish_game(session, winner=winner)
            logger.info("game finished during voting game_id=%s winner=%s round=%s", session["game_id"], winner, session["round"])
            finish_phase_event = build_phase_change_event(session)
            game_over_event = build_game_over_event(session)
            session["public_events"].extend([finish_phase_event, game_over_event])
            yield session, finish_phase_event
            yield session, game_over_event


def run_voting_action(
    session: GameSession,
    state_machine: GameStateMachine,
) -> tuple[GameSession, list[dict[str, object]]]:
    events: list[dict[str, object]] = []
    updated_session = session
    for updated_session, event in stream_voting_action(session, state_machine):
        events.append(event)
    return updated_session, events
