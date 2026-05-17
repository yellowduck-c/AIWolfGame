from __future__ import annotations

import logging
from collections.abc import Iterator

from game_engine.actions.day_speech import run_day_speech_action, stream_day_speech_action
from game_engine.actions.finish import run_finish_action, stream_finish_action
from game_engine.actions.night import run_night_action, stream_night_action
from game_engine.actions.voting import run_voting_action, stream_voting_action
from game_engine.models import GamePhase, GameSession, GameStatus
from game_engine.state_machine import GameStateMachine

logger = logging.getLogger(__name__)


class PhaseDrivenExecutor:
    def __init__(self, state_machine: GameStateMachine | None = None) -> None:
        self.state_machine = state_machine or GameStateMachine()

    def _advance_after_phase(self, session: GameSession) -> GameSession:
        if session["status"] == GameStatus.FINISHED:
            return session

        current_phase = GamePhase(session["phase"])
        if current_phase == GamePhase.NIGHT:
            session, finish_events = run_finish_action(session, self.state_machine)
            if finish_events:
                logger.info(
                    "finish check emitted game_id=%s phase=%s round=%s event_count=%s",
                    session["game_id"],
                    session["phase"],
                    session["round"],
                    len(finish_events),
                )
            if session["status"] == GameStatus.FINISHED:
                return session

        return self.state_machine.advance_phase(session)

    def run_current_phase(self, session: GameSession) -> tuple[GameSession, list[dict[str, object]]]:
        current_phase = GamePhase(session["phase"])
        logger.info("phase execution start game_id=%s phase=%s round=%s", session["game_id"], current_phase.value, session["round"])
        if current_phase == GamePhase.NIGHT:
            return run_night_action(session, self.state_machine)
        if current_phase == GamePhase.DAY_SPEECH:
            return run_day_speech_action(session, self.state_machine)
        if current_phase == GamePhase.VOTING:
            return run_voting_action(session, self.state_machine)
        return run_finish_action(session, self.state_machine)

    def stream_current_phase(self, session: GameSession) -> Iterator[tuple[GameSession, dict[str, object]]]:
        current_phase = GamePhase(session["phase"])
        logger.info("phase execution start game_id=%s phase=%s round=%s", session["game_id"], current_phase.value, session["round"])
        if current_phase == GamePhase.NIGHT:
            yield from stream_night_action(session, self.state_machine)
            return
        if current_phase == GamePhase.DAY_SPEECH:
            yield from stream_day_speech_action(session, self.state_machine)
            return
        if current_phase == GamePhase.VOTING:
            yield from stream_voting_action(session, self.state_machine)
            return
        yield from stream_finish_action(session, self.state_machine)

    def run_round(self, session: GameSession) -> tuple[GameSession, list[dict[str, object]]]:
        events: list[dict[str, object]] = []

        current_phase = GamePhase(session["phase"])
        if current_phase != GamePhase.NIGHT:
            session, phase_events = self.run_current_phase(session)
            events.extend(phase_events)
            if session["status"] == GameStatus.FINISHED:
                return session, events
            current_phase = GamePhase(session["phase"])

        if current_phase == GamePhase.NIGHT:
            session, finish_events = run_finish_action(session, self.state_machine)
            events.extend(finish_events)
            if session["status"] == GameStatus.FINISHED:
                return session, events
            session = self.state_machine.advance_phase(session)

        session, phase_events = self.run_current_phase(session)
        events.extend(phase_events)
        if session["status"] == GameStatus.FINISHED:
            return session, events

        session, phase_events = self.run_current_phase(session)
        events.extend(phase_events)
        if session["status"] == GameStatus.FINISHED:
            return session, events

        session, phase_events = run_finish_action(session, self.state_machine)
        events.extend(phase_events)
        return session, events

    def iter_game(self, session: GameSession) -> Iterator[tuple[GameSession, list[dict[str, object]]]]:
        while session["status"] != GameStatus.FINISHED:
            session, phase_events = self.run_current_phase(session)
            logger.info(
                "phase execution complete game_id=%s phase=%s round=%s event_count=%s status=%s",
                session["game_id"],
                session["phase"],
                session["round"],
                len(phase_events),
                session["status"],
            )
            yield session, phase_events
            if session["status"] == GameStatus.FINISHED:
                break
            session = self._advance_after_phase(session)

    def iter_game_events(self, session: GameSession) -> Iterator[tuple[GameSession, dict[str, object]]]:
        while session["status"] != GameStatus.FINISHED:
            phase_event_count = 0
            for updated_session, event in self.stream_current_phase(session):
                session = updated_session
                phase_event_count += 1
                yield session, event
            logger.info(
                "phase execution complete game_id=%s phase=%s round=%s event_count=%s status=%s",
                session["game_id"],
                session["phase"],
                session["round"],
                phase_event_count,
                session["status"],
            )
            if session["status"] == GameStatus.FINISHED:
                break
            current_phase = GamePhase(session["phase"])
            if current_phase == GamePhase.NIGHT:
                finish_event_count = 0
                for updated_session, event in stream_finish_action(session, self.state_machine):
                    session = updated_session
                    finish_event_count += 1
                    yield session, event
                if finish_event_count:
                    logger.info(
                        "finish check emitted game_id=%s phase=%s round=%s event_count=%s",
                        session["game_id"],
                        session["phase"],
                        session["round"],
                        finish_event_count,
                    )
                if session["status"] == GameStatus.FINISHED:
                    break
            session = self.state_machine.advance_phase(session)

    def run(self, session: GameSession) -> tuple[GameSession, list[dict[str, object]]]:
        events: list[dict[str, object]] = []

        if GamePhase(session["phase"]) != GamePhase.NIGHT:
            session, round_events = self.run_round(session)
            events.extend(round_events)
            return session, events

        for session, phase_events in self.iter_game(session):
            events.extend(phase_events)
            if session["status"] == GameStatus.FINISHED:
                break

        return session, events
