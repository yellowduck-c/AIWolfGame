from __future__ import annotations

import logging
from collections.abc import Iterator

from agent.core.registry import agent_registry
from game_engine.decision_context import build_agent_decision_input
from game_engine.events import build_phase_change_event, build_speak_chunk_event, build_speak_event
from game_engine.models import GameSession
from game_engine.state_machine import GameStateMachine

logger = logging.getLogger(__name__)


def stream_day_speech_action(
    session: GameSession,
    state_machine: GameStateMachine,
) -> Iterator[tuple[GameSession, dict[str, object]]]:
    logger.info("day speech phase started game_id=%s round=%s", session["game_id"], session["round"])
    yield session, build_phase_change_event(session)

    for agent_snapshot in session["agents"]:
        if agent_snapshot["status"] != "alive":
            continue

        agent = agent_registry.get_agent(session["game_id"], agent_snapshot["id"])
        decision_input = build_agent_decision_input(
            session,
            agent_snapshot,
            agent,
            legal_actions={"type": "speak", "allowed": True},
        )
        decision = agent.speak_streaming(decision_input)
        logger.info(
            "agent speech generated game_id=%s round=%s agent_id=%s role=%s content_length=%s chunk_count=%s",
            session["game_id"],
            session["round"],
            agent_snapshot["id"],
            agent_snapshot["role"],
            len(decision.content),
            len(decision.chunks),
        )
        partial_content = ""
        for chunk in decision.chunks:
            partial_content = f"{partial_content}，{chunk}" if partial_content else chunk
            yield session, build_speak_chunk_event(
                agent_id=agent_snapshot["id"],
                role=agent_snapshot["role"],
                content=partial_content,
            )
        event = build_speak_event(
            agent_id=agent_snapshot["id"],
            role=agent_snapshot["role"],
            content=decision.content,
        )
        session["public_events"].append(event)
        for public_agent_snapshot in session["agents"]:
            public_agent = agent_registry.get_agent(session["game_id"], public_agent_snapshot["id"])
            public_agent.observe_public_event(event)
        yield session, event


def run_day_speech_action(
    session: GameSession,
    state_machine: GameStateMachine,
) -> tuple[GameSession, list[dict[str, object]]]:
    events: list[dict[str, object]] = []
    updated_session = session
    for updated_session, event in stream_day_speech_action(session, state_machine):
        events.append(event)
    return updated_session, events
