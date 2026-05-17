from __future__ import annotations

import logging
from collections.abc import Iterator

from game_engine.events import build_game_over_event, build_phase_change_event
from game_engine.models import GameSession
from game_engine.state_machine import GameStateMachine

logger = logging.getLogger(__name__)


def stream_finish_action(
    session: GameSession,
    state_machine: GameStateMachine,
) -> Iterator[tuple[GameSession, dict[str, object]]]:
    winner = state_machine.calculate_winner(session)
    if winner is None:
        logger.debug("finish check skipped game_id=%s round=%s", session["game_id"], session["round"])
        return

    session = state_machine.finish_game(session, winner=winner)
    logger.info("finish action resolved game_id=%s winner=%s round=%s", session["game_id"], winner, session["round"])
    yield session, build_phase_change_event(session)
    yield session, build_game_over_event(session)


def run_finish_action(
    session: GameSession,
    state_machine: GameStateMachine,
) -> tuple[GameSession, list[dict[str, object]]]:
    events: list[dict[str, object]] = []
    updated_session = session
    for updated_session, event in stream_finish_action(session, state_machine):
        events.append(event)
    return updated_session, events
