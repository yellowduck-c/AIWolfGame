import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent import build_agent
from agent.core.registry import agent_registry
from agent.state.schemas import SkillDecision, VoteDecision
from cache.client import close_redis_client
from cache.keys import game_event_log_key, game_session_key
from cache.session_store import GameSessionStore
from game_engine.actions.day_speech import run_day_speech_action
from game_engine.actions.night import run_night_action
from game_engine.actions.voting import run_voting_action
from game_engine.decision_context import (
    SEER_INSPECTION_FACT_TYPE,
    WITCH_HEAL_FACT_TYPE,
    WITCH_POISON_FACT_TYPE,
    build_agent_decision_input,
    build_skill_legal_actions,
    build_vote_legal_actions,
)
from game_engine.executor import PhaseDrivenExecutor
from game_engine.models import GameStatus
from game_engine.service import GameCommandService, build_game_started_event, build_mock_agents, build_runtime_agents
from game_engine.state_machine import GameStateMachine
from llm_service.client import LLMServiceClient


@pytest.mark.asyncio
async def test_create_game_accepts_twelve_player_preset_with_idiot() -> None:
    service = GameCommandService()
    session_store = GameSessionStore()
    role_counts = {"werewolf": 4, "seer": 1, "witch": 1, "hunter": 1, "idiot": 1, "villager": 4}
    assigned_roles = [
        {"id": 1, "role_key": "werewolf"},
        {"id": 2, "role_key": "werewolf"},
        {"id": 3, "role_key": "werewolf"},
        {"id": 4, "role_key": "werewolf"},
        {"id": 5, "role_key": "seer"},
        {"id": 6, "role_key": "witch"},
        {"id": 7, "role_key": "hunter"},
        {"id": 8, "role_key": "idiot"},
        {"id": 9, "role_key": "villager"},
        {"id": 10, "role_key": "villager"},
        {"id": 11, "role_key": "villager"},
        {"id": 12, "role_key": "villager"},
    ]

    session, _ = await service.create_game(player_count=12, role_counts=role_counts, assigned_roles=assigned_roles)

    try:
        stored_session = await session_store.get_session(session["game_id"])

        assert stored_session is not None
        assert stored_session["role_counts"] == role_counts
        assert any(agent["role"] == "白痴" for agent in session["agents"])
        assert len(session["agents"]) == 12
    finally:
        await service.handle_reset(session["game_id"])
        await close_redis_client()


@pytest.mark.asyncio
async def test_create_game_persists_overview_and_initializes_empty_event_log() -> None:
    service = GameCommandService()
    session_store = GameSessionStore()

    session, _ = await service.create_game(player_count=6, role_counts={"werewolf": 2, "seer": 1, "witch": 1, "hunter": 0, "idiot": 0, "villager": 2})

    try:
        stored_session = await session_store.get_session(session["game_id"])
        stored_events = await session_store.get_events(session["game_id"])

        assert stored_session is not None
        assert stored_session["game_id"] == session["game_id"]
        assert stored_session["player_count"] == 6
        assert stored_session["role_counts"] == {"werewolf": 2, "seer": 1, "witch": 1, "hunter": 0, "idiot": 0, "villager": 2}
        assert stored_session["created_at"]
        assert "public_events" not in stored_session
        assert stored_events == []
    finally:
        await service.handle_reset(session["game_id"])
        await close_redis_client()


@pytest.mark.asyncio
async def test_stream_game_events_persists_ordered_runtime_event_log() -> None:
    service = GameCommandService()
    session_store = GameSessionStore()

    session, _ = await service.create_game(player_count=6, role_counts={"werewolf": 2, "seer": 1, "witch": 1, "hunter": 0, "idiot": 0, "villager": 2})

    try:
        collected_events = [event["event"] async for _, event in service.stream_game_events(session["game_id"])]

        stored_events = await session_store.get_events(session["game_id"])

        assert stored_events
        assert stored_events[0]["event"] == collected_events[0]
        assert collected_events[-1] == "GAME_OVER"
        assert stored_events[-1]["event"] == "GAME_OVER"
        assert all(event["game_id"] == session["game_id"] for event in stored_events)
        assert all("timestamp" in event for event in stored_events)
        assert all("phase" in event for event in stored_events)
        assert all("round" in event for event in stored_events)
        assert all(event["event"] != "AGENT_SPEAK_CHUNK" for event in stored_events)
        assert any(event["event"] == "AGENT_SPEAK" for event in stored_events)
    finally:
        await service.handle_reset(session["game_id"])
        await close_redis_client()


@pytest.mark.asyncio
async def test_stream_game_events_keeps_runtime_session_summary_without_dialogue_history() -> None:
    service = GameCommandService()
    session_store = GameSessionStore()

    session, _ = await service.create_game(player_count=6, role_counts={"werewolf": 2, "seer": 1, "witch": 1, "hunter": 0, "idiot": 0, "villager": 2})

    try:
        async for _updated_session, _event in service.stream_game_events(session["game_id"]):
            pass

        stored_session = await session_store.get_session(session["game_id"])

        assert stored_session is not None
        assert "public_events" not in stored_session
        assert stored_session["winner"] in {"狼人", "好人"}
        assert stored_session["status"] == "finished"
    finally:
        await service.handle_reset(session["game_id"])
        await close_redis_client()


@pytest.mark.asyncio
async def test_handle_reset_preserves_session_and_event_log_history() -> None:
    service = GameCommandService()
    session_store = GameSessionStore()

    session, _ = await service.create_game(player_count=6, role_counts={"werewolf": 2, "seer": 1, "witch": 1, "hunter": 0, "idiot": 0, "villager": 2})
    await session_store.append_event(session["game_id"], {"event": "TEST_EVENT"})

    await service.handle_reset(session["game_id"])

    stored_session = await session_store.get_session(session["game_id"])
    stored_events = await session_store.get_events(session["game_id"])

    assert stored_session is not None
    assert stored_session["game_id"] == session["game_id"]
    assert stored_events == [{"event": "TEST_EVENT"}]

    await close_redis_client()


@pytest.mark.asyncio
async def test_handle_stop_persists_game_over_event_and_retains_history() -> None:
    service = GameCommandService()
    session_store = GameSessionStore()

    session, _ = await service.create_game(player_count=6, role_counts={"werewolf": 2, "seer": 1, "witch": 1, "hunter": 0, "idiot": 0, "villager": 2})
    await session_store.append_event(session["game_id"], {"event": "PHASE_CHANGE", "game_id": session["game_id"], "phase": "night", "round": 1, "timestamp": "seed"})

    stop_event = await service.handle_stop(session["game_id"])
    stored_session = await session_store.get_session(session["game_id"])
    stored_events = await session_store.get_events(session["game_id"])

    assert stop_event["event"] == "GAME_OVER"
    assert stop_event["winner"] == "stopped"
    assert stored_session is not None
    assert stored_session["status"] == "finished"
    assert stored_session["winner"] == "stopped"
    assert stored_session["ended_at"]
    assert "public_events" not in stored_session
    assert stored_events[-1]["event"] == "GAME_OVER"
    assert stored_events[-1]["winner"] == "stopped"
    assert stored_events[-1]["game_id"] == session["game_id"]

    await close_redis_client()


def build_runtime_test_session(game_id: str = "runtime-test") -> tuple[GameStateMachine, dict[str, object]]:
    state_machine = GameStateMachine()
    session = state_machine.create_initial_session(game_id=game_id, agents=build_mock_agents())
    agent_registry.register_game_agents(session["game_id"], build_runtime_agents(session))
    return state_machine, session


@pytest.fixture(autouse=True)
def reset_llm_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("llm_service.client.settings.llm_provider", "mock")
    monkeypatch.setattr("llm_service.client.settings.llm_api_key", "")


def build_custom_runtime_session(game_id: str, agents: list[dict[str, object]]) -> tuple[GameStateMachine, dict[str, object]]:
    state_machine = GameStateMachine()
    session = state_machine.create_initial_session(game_id=game_id, agents=agents)
    agent_registry.register_game_agents(session["game_id"], build_runtime_agents(session))
    return state_machine, session


def test_base_agent_builds_llm_client_without_circular_import() -> None:
    agent = build_agent(player_id=1, role="村民", camp="好人")

    assert agent.llm_client is not None
    assert agent.llm_client.__class__.__name__ == "LLMServiceClient"


    werewolf_agent = build_agent(player_id=1, role="狼人", camp="狼人")
    seer_agent = build_agent(player_id=2, role="预言家", camp="好人")
    witch_agent = build_agent(player_id=3, role="女巫", camp="好人")
    hunter_agent = build_agent(player_id=4, role="猎人", camp="好人")
    idiot_agent = build_agent(player_id=5, role="白痴", camp="好人")
    villager_agent = build_agent(player_id=6, role="村民", camp="好人")

    assert werewolf_agent.get_role_profile().role == "狼人"
    assert seer_agent.get_role_profile().role == "预言家"
    assert witch_agent.get_role_profile().role == "女巫"
    assert hunter_agent.get_role_profile().role == "猎人"
    assert idiot_agent.get_role_profile().role == "白痴"
    assert villager_agent.get_role_profile().role == "村民"
    assert werewolf_agent.get_role_profile().behavior_tags != seer_agent.get_role_profile().behavior_tags


def test_agent_enriches_decision_input_with_role_specialization() -> None:
    state_machine, session = build_runtime_test_session("role-specialization")

    try:
        seer_snapshot = next(agent for agent in session["agents"] if agent["role"] == "预言家")
        seer_agent = agent_registry.get_agent(session["game_id"], seer_snapshot["id"])
        decision_input = build_agent_decision_input(
            session,
            seer_snapshot,
            seer_agent,
            legal_actions={"type": "speak", "allowed": True},
        )

        enriched = seer_agent.enrich_decision_input("speech", decision_input)

        assert enriched.specialization["action_type"] == "speech"
        assert enriched.specialization["role_profile"]["role"] == "预言家"
        assert enriched.specialization["action_guidance"]["goal"]
        assert "behavior_tags" in enriched.specialization
        assert enriched.specialization["role_instruction"]
        assert enriched.specialization["action_guidance_instruction"]
    finally:
        agent_registry.clear_game(session["game_id"])


def test_prompt_builder_includes_role_specific_guidance() -> None:
    from llm_service.prompt_builder import build_speech_prompt

    state_machine, session = build_runtime_test_session("role-prompt-guidance")

    try:
        werewolf_snapshot = next(agent for agent in session["agents"] if agent["role"] == "狼人")
        seer_snapshot = next(agent for agent in session["agents"] if agent["role"] == "预言家")
        werewolf_agent = agent_registry.get_agent(session["game_id"], werewolf_snapshot["id"])
        seer_agent = agent_registry.get_agent(session["game_id"], seer_snapshot["id"])

        werewolf_input = werewolf_agent.enrich_decision_input(
            "speech",
            build_agent_decision_input(session, werewolf_snapshot, werewolf_agent, legal_actions={"type": "speak", "allowed": True}),
        )
        seer_input = seer_agent.enrich_decision_input(
            "speech",
            build_agent_decision_input(session, seer_snapshot, seer_agent, legal_actions={"type": "speak", "allowed": True}),
        )

        werewolf_prompt = build_speech_prompt(werewolf_input)
        seer_prompt = build_speech_prompt(seer_input)

        assert "你的身份定位：夜间与同伴协作、白天隐藏身份的狼人" in werewolf_prompt
        assert "你的身份定位：拥有查验能力、需要逐步建立公信力的预言家" in seer_prompt
        assert werewolf_prompt != seer_prompt
    finally:
        agent_registry.clear_game(session["game_id"])


def test_phase_rollover_returns_to_night_after_voting() -> None:
    state_machine = GameStateMachine()
    session = state_machine.create_initial_session(
        game_id="round-rollover",
        agents=[
            {"id": 1, "role": "狼人", "camp": "狼人", "status": "alive"},
            {"id": 2, "role": "村民", "camp": "好人", "status": "alive"},
            {"id": 3, "role": "预言家", "camp": "好人", "status": "alive"},
        ],
    )

    session = state_machine.advance_phase(session)
    assert session["phase"] == "day_speech"
    assert session["round"] == 1

    session = state_machine.advance_phase(session)
    assert session["phase"] == "voting"
    assert session["round"] == 1

    session = state_machine.advance_phase(session)
    assert session["phase"] == "night"
    assert session["round"] == 2


class StaticMemory:
    def __init__(self) -> None:
        self.private_facts: list[dict[str, object]] = []

    def to_summary(self) -> dict[str, object]:
        return {"private_facts": list(self.private_facts)}


class StaticDecisionAgent:
    def __init__(self, *, vote_target_id: int) -> None:
        self.vote_target_id = vote_target_id
        self.memory = StaticMemory()

    def speak_streaming(self, _decision_input):
        return type("SpeechDecision", (), {"content": "保持观察。", "chunks": ["保持观察。"]})()

    def vote(self, _decision_input):
        return VoteDecision(target_id=self.vote_target_id)

    def observe_public_event(self, _event: dict[str, object]) -> None:
        return None


class PassiveObserverAgent(StaticDecisionAgent):
    def __init__(self) -> None:
        super().__init__(vote_target_id=0)

    def observe_public_event(self, _event: dict[str, object]) -> None:
        return None


class StubRegistry:
    def __init__(self, agents: dict[int, StaticDecisionAgent]) -> None:
        self.agents = agents

    def get_agent(self, _game_id: str, agent_id: int):
        return self.agents[agent_id]


def test_day_speech_action_does_not_advance_phase() -> None:
    state_machine = GameStateMachine()
    session = state_machine.create_initial_session(
        game_id="day-speech-phase-ownership",
        agents=[
            {"id": 1, "role": "狼人", "camp": "狼人", "status": "alive"},
            {"id": 2, "role": "村民", "camp": "好人", "status": "alive"},
        ],
    )
    session["phase"] = "day_speech"

    class SpeechOnlyAgent(StaticDecisionAgent):
        pass

    stub_registry = StubRegistry({
        1: SpeechOnlyAgent(vote_target_id=2),
        2: SpeechOnlyAgent(vote_target_id=1),
    })

    original_registry = agent_registry
    try:
        from game_engine.actions import day_speech as day_speech_module

        day_speech_module.agent_registry = stub_registry
        updated_session, events = run_day_speech_action(session, state_machine)
    finally:
        from game_engine.actions import day_speech as day_speech_module

        day_speech_module.agent_registry = original_registry

    assert updated_session["phase"] == "day_speech"
    assert events[0]["event"] == "PHASE_CHANGE"
    assert events[0]["phase"] == "day_speech"


def test_voting_action_emits_peaceful_day_on_tie() -> None:
    state_machine = GameStateMachine()
    session = state_machine.create_initial_session(
        game_id="voting-peaceful-day",
        agents=[
            {"id": 1, "role": "狼人", "camp": "狼人", "status": "alive"},
            {"id": 2, "role": "村民", "camp": "好人", "status": "alive"},
            {"id": 3, "role": "村民", "camp": "好人", "status": "alive"},
            {"id": 4, "role": "村民", "camp": "好人", "status": "alive"},
        ],
    )
    session["phase"] = "voting"

    stub_registry = StubRegistry({
        1: StaticDecisionAgent(vote_target_id=2),
        2: StaticDecisionAgent(vote_target_id=1),
        3: StaticDecisionAgent(vote_target_id=1),
        4: StaticDecisionAgent(vote_target_id=2),
    })

    original_registry = agent_registry
    try:
        from game_engine.actions import voting as voting_module

        voting_module.agent_registry = stub_registry
        updated_session, events = run_voting_action(session, state_machine)
    finally:
        from game_engine.actions import voting as voting_module

        voting_module.agent_registry = original_registry

    assert events[0]["event"] == "PHASE_CHANGE"
    assert events[0]["phase"] == "voting"
    assert [event["event"] for event in events].count("AGENT_VOTE") == 4
    assert all(event["event"] != "AGENT_STATUS_CHANGE" for event in events)
    assert all(agent["status"] == "alive" for agent in updated_session["agents"])
    assert updated_session["status"] != "finished"


    state_machine = GameStateMachine()
    session = state_machine.create_initial_session(
        game_id="voting-phase-ownership",
        agents=[
            {"id": 1, "role": "狼人", "camp": "狼人", "status": "alive"},
            {"id": 2, "role": "村民", "camp": "好人", "status": "dead"},
            {"id": 3, "role": "预言家", "camp": "好人", "status": "dead"},
            {"id": 4, "role": "村民", "camp": "好人", "status": "alive"},
            {"id": 5, "role": "村民", "camp": "好人", "status": "alive"},
            {"id": 6, "role": "村民", "camp": "好人", "status": "dead"},
        ],
    )
    session["phase"] = "voting"

    stub_registry = StubRegistry({
        1: StaticDecisionAgent(vote_target_id=5),
        2: PassiveObserverAgent(),
        3: PassiveObserverAgent(),
        4: StaticDecisionAgent(vote_target_id=1),
        5: StaticDecisionAgent(vote_target_id=1),
        6: PassiveObserverAgent(),
    })

    original_registry = agent_registry
    try:
        from game_engine.actions import voting as voting_module

        voting_module.agent_registry = stub_registry
        updated_session, events = run_voting_action(session, state_machine)
    finally:
        from game_engine.actions import voting as voting_module

        voting_module.agent_registry = original_registry

    assert events[0]["event"] == "PHASE_CHANGE"
    assert events[0]["phase"] == "voting"
    assert any(event["event"] == "AGENT_STATUS_CHANGE" for event in events)


def test_calculate_winner_for_good_camp() -> None:
    state_machine = GameStateMachine()
    session = state_machine.create_initial_session(
        game_id="winner-good",
        agents=[
            {"id": 1, "role": "狼人", "camp": "狼人", "status": "dead"},
            {"id": 2, "role": "村民", "camp": "好人", "status": "alive"},
            {"id": 3, "role": "预言家", "camp": "好人", "status": "alive"},
        ],
    )

    assert state_machine.calculate_winner(session) == "好人"


def test_calculate_winner_for_wolf_camp() -> None:
    state_machine = GameStateMachine()
    session = state_machine.create_initial_session(
        game_id="winner-wolf",
        agents=[
            {"id": 1, "role": "狼人", "camp": "狼人", "status": "alive"},
            {"id": 2, "role": "村民", "camp": "好人", "status": "alive"},
            {"id": 3, "role": "预言家", "camp": "好人", "status": "dead"},
        ],
    )

    assert state_machine.calculate_winner(session) == "狼人"


def test_calculate_winner_returns_none_when_game_continues() -> None:
    state_machine = GameStateMachine()
    session = state_machine.create_initial_session(
        game_id="winner-none",
        agents=[
            {"id": 1, "role": "狼人", "camp": "狼人", "status": "alive"},
            {"id": 2, "role": "村民", "camp": "好人", "status": "alive"},
            {"id": 3, "role": "预言家", "camp": "好人", "status": "alive"},
        ],
    )

    assert state_machine.calculate_winner(session) is None


@pytest.mark.asyncio
async def test_decision_context_isolated_by_role() -> None:
    state_machine, session = build_runtime_test_session("decision-context")

    try:
        werewolf_snapshot = next(agent for agent in session["agents"] if agent["role"] == "狼人")
        villager_snapshot = next(agent for agent in session["agents"] if agent["role"] == "村民")
        seer_snapshot = next(agent for agent in session["agents"] if agent["role"] == "预言家")

        werewolf_agent = agent_registry.get_agent(session["game_id"], werewolf_snapshot["id"])
        villager_agent = agent_registry.get_agent(session["game_id"], villager_snapshot["id"])
        seer_agent = agent_registry.get_agent(session["game_id"], seer_snapshot["id"])

        werewolf_input = build_agent_decision_input(
            session,
            werewolf_snapshot,
            werewolf_agent,
            legal_actions=build_skill_legal_actions(session, werewolf_snapshot),
        )
        villager_input = build_agent_decision_input(
            session,
            villager_snapshot,
            villager_agent,
            legal_actions=build_skill_legal_actions(session, villager_snapshot),
        )
        seer_input = build_agent_decision_input(
            session,
            seer_snapshot,
            seer_agent,
            legal_actions=build_skill_legal_actions(session, seer_snapshot),
        )

        assert werewolf_input.camp_shared_state["teammates"]
        assert villager_input.camp_shared_state == {}
        assert werewolf_input.private_state["self"]["role"] == "狼人"
        assert villager_input.private_state["self"]["role"] == "村民"
        assert seer_input.private_state["skill"] == "inspect"
        assert all(target_id not in {1, 2} for target_id in werewolf_input.legal_actions["targets"])
    finally:
        agent_registry.clear_game(session["game_id"])


def test_idiot_decision_context_has_no_skill_or_camp_shared_state() -> None:
    state_machine, session = build_custom_runtime_session(
        "idiot-context",
        [
            {"id": 1, "role": "狼人", "camp": "狼人", "status": "alive"},
            {"id": 2, "role": "白痴", "camp": "好人", "status": "alive"},
            {"id": 3, "role": "村民", "camp": "好人", "status": "alive"},
            {"id": 4, "role": "预言家", "camp": "好人", "status": "alive"},
        ],
    )

    try:
        idiot_snapshot = next(agent for agent in session["agents"] if agent["role"] == "白痴")
        idiot_agent = agent_registry.get_agent(session["game_id"], idiot_snapshot["id"])
        decision_input = build_agent_decision_input(
            session,
            idiot_snapshot,
            idiot_agent,
            legal_actions=build_skill_legal_actions(session, idiot_snapshot),
        )

        assert decision_input.camp_shared_state == {}
        assert decision_input.private_state["self"]["role"] == "白痴"
        assert "skill" not in decision_input.private_state
        assert decision_input.legal_actions["allowed"] is False
        assert decision_input.legal_actions["skill"] is None
    finally:
        agent_registry.clear_game(session["game_id"])


@pytest.mark.asyncio
async def test_voting_excludes_self_from_candidates_and_emits_votes() -> None:
    state_machine, session = build_runtime_test_session("voting-action")

    try:
        alive_snapshot = next(agent for agent in session["agents"] if agent["status"] == "alive")
        alive_agent = agent_registry.get_agent(session["game_id"], alive_snapshot["id"])
        vote_input = build_agent_decision_input(
            session,
            alive_snapshot,
            alive_agent,
            legal_actions=build_vote_legal_actions(session, alive_snapshot),
        )
        assert alive_snapshot["id"] not in vote_input.legal_actions["candidates"]

        session["phase"] = "day_speech"
        updated_session, events = run_voting_action(session, state_machine)
        vote_events = [event for event in events if event["event"] == "AGENT_VOTE"]
        status_events = [event for event in events if event["event"] == "AGENT_STATUS_CHANGE"]

        assert vote_events
        assert status_events or updated_session["status"] == "finished"
        assert any(agent["status"] == "dead" for agent in updated_session["agents"]) or updated_session["status"] == "finished"
    finally:
        agent_registry.clear_game(session["game_id"])


def test_night_action_uses_declarative_role_order_and_skips_non_active_roles() -> None:
    state_machine = GameStateMachine()
    session = state_machine.create_initial_session(
        game_id="night-role-order",
        agents=[
            {"id": 1, "role": "村民", "camp": "好人", "status": "alive"},
            {"id": 2, "role": "女巫", "camp": "好人", "status": "alive"},
            {"id": 3, "role": "猎人", "camp": "好人", "status": "alive"},
            {"id": 4, "role": "预言家", "camp": "好人", "status": "alive"},
            {"id": 5, "role": "狼人", "camp": "狼人", "status": "alive"},
        ],
    )
    session["phase"] = "night"

    call_order: list[tuple[int, str]] = []

    class TrackingRoleAgent(StaticDecisionAgent):
        def __init__(self, agent_id: int, *, skill: str, target_id: int | None) -> None:
            super().__init__(vote_target_id=1)
            self.memory = StaticMemory()
            self.agent_id = agent_id
            self.skill = skill
            self.target_id = target_id

        def use_skill(self, decision_input):
            call_order.append((self.agent_id, decision_input.legal_actions["skill"]))
            return SkillDecision(skill=self.skill, target_id=self.target_id)

        def observe_private_fact(self, fact: dict[str, object]) -> None:
            self.memory.private_facts.append(fact)

    class ForbiddenNightAgent(PassiveObserverAgent):
        def use_skill(self, _decision_input):
            raise AssertionError("non-active night role should not use skills")

    stub_registry = StubRegistry({
        1: ForbiddenNightAgent(),
        2: TrackingRoleAgent(2, skill="skip", target_id=None),
        3: ForbiddenNightAgent(),
        4: TrackingRoleAgent(4, skill="inspect", target_id=1),
        5: TrackingRoleAgent(5, skill="kill", target_id=1),
    })

    original_registry = agent_registry
    try:
        from game_engine.actions import night as night_module

        night_module.agent_registry = stub_registry
        _, events = run_night_action(session, state_machine)
    finally:
        from game_engine.actions import night as night_module

        night_module.agent_registry = original_registry

    skill_roles = [event["role"] for event in events if event["event"] == "AGENT_SKILL"]

    assert call_order == [(5, "kill"), (4, "inspect"), (2, "brew")]
    assert skill_roles[:3] == ["狼人", "预言家", "女巫"]


@pytest.mark.asyncio
async def test_night_action_emits_skill_events_and_kills_non_wolf_target() -> None:
    state_machine, session = build_runtime_test_session("night-action")

    try:
        updated_session, events = run_night_action(session, state_machine)
        skill_events = [event for event in events if event["event"] == "AGENT_SKILL"]
        status_events = [event for event in events if event["event"] == "AGENT_STATUS_CHANGE"]
        heal_events = [event for event in skill_events if event["skill"] == "heal"]

        assert skill_events
        assert heal_events or status_events
        if status_events:
            eliminated_agent_id = status_events[0]["id"]
            eliminated_snapshot = next(agent for agent in updated_session["agents"] if agent["id"] == eliminated_agent_id)
            assert eliminated_snapshot["status"] == "dead"
        else:
            assert heal_events
    finally:
        agent_registry.clear_game(session["game_id"])


def test_night_action_records_seer_private_fact_only_for_seer() -> None:
    state_machine, session = build_runtime_test_session("seer-private-fact")

    try:
        run_night_action(session, state_machine)
        seer_snapshot = next(agent for agent in session["agents"] if agent["role"] == "预言家")
        villager_snapshot = next(agent for agent in session["agents"] if agent["role"] == "村民")
        seer_agent = agent_registry.get_agent(session["game_id"], seer_snapshot["id"])
        villager_agent = agent_registry.get_agent(session["game_id"], villager_snapshot["id"])

        assert any(fact["type"] == SEER_INSPECTION_FACT_TYPE for fact in seer_agent.memory.private_facts)
        assert all(fact["type"] != SEER_INSPECTION_FACT_TYPE for fact in villager_agent.memory.private_facts)
    finally:
        agent_registry.clear_game(session["game_id"])


def test_witch_joint_decision_becomes_available_after_wolf_target_is_known() -> None:
    state_machine, session = build_runtime_test_session("witch-joint-window")

    try:
        witch_snapshot = next(agent for agent in session["agents"] if agent["role"] == "女巫")
        witch_agent = agent_registry.get_agent(session["game_id"], witch_snapshot["id"])

        legal_actions = build_skill_legal_actions(session, witch_snapshot, witch_agent)
        assert legal_actions["allowed"] is True
        assert legal_actions["can_heal"] is False
        assert legal_actions["can_poison"] is True

        session["night_pending_target_id"] = 6
        legal_actions = build_skill_legal_actions(session, witch_snapshot, witch_agent)
        assert legal_actions["allowed"] is True
        assert legal_actions["can_heal"] is True
        assert legal_actions["can_poison"] is True
        assert legal_actions["wolf_target_id"] == 6
        assert witch_snapshot["id"] not in legal_actions["targets"]
    finally:
        session.pop("night_pending_target_id", None)
        agent_registry.clear_game(session["game_id"])


def test_seer_can_still_act_when_werewolf_is_processed_first() -> None:
    state_machine, session = build_runtime_test_session("seer-after-wolf")

    try:
        updated_session, events = run_night_action(session, state_machine)
        seer_skill_events = [event for event in events if event["event"] == "AGENT_SKILL" and event["role"] == "预言家"]
        seer_snapshot = next(agent for agent in updated_session["agents"] if agent["role"] == "预言家")
        seer_agent = agent_registry.get_agent(session["game_id"], seer_snapshot["id"])

        assert seer_skill_events
        assert any(fact["type"] == SEER_INSPECTION_FACT_TYPE for fact in seer_agent.memory.private_facts)
    finally:
        agent_registry.clear_game(session["game_id"])


    state_machine, session = build_runtime_test_session("witch-resources")

    try:
        witch_snapshot = next(agent for agent in session["agents"] if agent["role"] == "女巫")
        witch_agent = agent_registry.get_agent(session["game_id"], witch_snapshot["id"])

        session["night_pending_target_id"] = 6
        witch_input = build_agent_decision_input(
            session,
            witch_snapshot,
            witch_agent,
            legal_actions=build_skill_legal_actions(session, witch_snapshot, witch_agent),
        )
        assert witch_input.private_state["witch_resources"] == {
            "heal_available": True,
            "poison_available": True,
        }
        assert witch_input.private_state["night_context"]["wolf_target_id"] == 6
        assert witch_input.legal_actions["can_heal"] is True
        assert witch_input.legal_actions["can_poison"] is True

        run_night_action(session, state_machine)

        assert any(fact["type"] == WITCH_HEAL_FACT_TYPE for fact in witch_agent.memory.private_facts)
        assert all(fact["type"] != WITCH_POISON_FACT_TYPE for fact in witch_agent.memory.private_facts)

        session["night_pending_target_id"] = 5
        session["witch_potion_used"] = True
        next_round_input = build_agent_decision_input(
            session,
            witch_snapshot,
            witch_agent,
            legal_actions=build_skill_legal_actions(session, witch_snapshot, witch_agent),
        )
        assert next_round_input.private_state["witch_resources"] == {
            "heal_available": False,
            "poison_available": True,
        }
        assert next_round_input.legal_actions["allowed"] is False
        assert next_round_input.legal_actions["potion_used_tonight"] is True
        assert next_round_input.legal_actions["can_poison"] is False
    finally:
        session.pop("night_pending_target_id", None)
        agent_registry.clear_game(session["game_id"])


def test_witch_joint_decision_still_respects_single_potion_per_night() -> None:
    state_machine, session = build_runtime_test_session("witch-single-potion")

    try:
        witch_snapshot = next(agent for agent in session["agents"] if agent["role"] == "女巫")
        witch_agent = agent_registry.get_agent(session["game_id"], witch_snapshot["id"])

        session["night_pending_target_id"] = 6
        legal_actions = build_skill_legal_actions(session, witch_snapshot, witch_agent)
        assert legal_actions["allowed"] is True
        assert legal_actions["can_heal"] is True
        assert legal_actions["can_poison"] is True

        session["witch_potion_used"] = True
        used_actions = build_skill_legal_actions(session, witch_snapshot, witch_agent)
        assert used_actions["allowed"] is False
        assert used_actions["can_heal"] is False
        assert used_actions["can_poison"] is False
        assert used_actions["potion_used_tonight"] is True
    finally:
        session.pop("night_pending_target_id", None)
        session.pop("witch_potion_used", None)
        agent_registry.clear_game(session["game_id"])


def test_witch_is_only_asked_once_per_night() -> None:
    state_machine = GameStateMachine()
    session = state_machine.create_initial_session(
        game_id="witch-single-call",
        agents=[
            {"id": 1, "role": "狼人", "camp": "狼人", "status": "alive"},
            {"id": 2, "role": "女巫", "camp": "好人", "status": "alive"},
            {"id": 3, "role": "预言家", "camp": "好人", "status": "alive"},
            {"id": 4, "role": "村民", "camp": "好人", "status": "alive"},
        ],
    )
    session["phase"] = "night"

    witch_calls = 0

    class CountingNightAgent(StaticDecisionAgent):
        def __init__(self, *, skill: str, target_id: int | None) -> None:
            super().__init__(vote_target_id=1)
            self.memory = StaticMemory()
            self.skill = skill
            self.target_id = target_id

        def use_skill(self, _decision_input):
            return SkillDecision(skill=self.skill, target_id=self.target_id)

        def observe_private_fact(self, fact: dict[str, object]) -> None:
            self.memory.private_facts.append(fact)

    class CountingWitchAgent(CountingNightAgent):
        def use_skill(self, decision_input):
            nonlocal witch_calls
            witch_calls += 1
            return super().use_skill(decision_input)

    stub_registry = StubRegistry({
        1: CountingNightAgent(skill="kill", target_id=3),
        2: CountingWitchAgent(skill="heal", target_id=3),
        3: CountingNightAgent(skill="inspect", target_id=1),
        4: PassiveObserverAgent(),
    })

    original_registry = agent_registry
    try:
        from game_engine.actions import night as night_module

        night_module.agent_registry = stub_registry
        _, events = run_night_action(session, state_machine)
    finally:
        from game_engine.actions import night as night_module

        night_module.agent_registry = original_registry

    witch_events = [event for event in events if event["event"] == "AGENT_SKILL" and event["role"] == "女巫"]

    assert witch_calls == 1
    assert len(witch_events) == 1
    assert witch_events[0]["skill"] == "heal"


def test_witch_heal_prevents_wolf_target_from_dying() -> None:
    state_machine, session = build_custom_runtime_session(
        "witch-heal",
        [
            {"id": 1, "role": "狼人", "camp": "狼人", "status": "alive"},
            {"id": 2, "role": "预言家", "camp": "好人", "status": "alive"},
            {"id": 3, "role": "女巫", "camp": "好人", "status": "alive"},
            {"id": 4, "role": "村民", "camp": "好人", "status": "alive"},
        ],
    )

    try:
        updated_session, events = run_night_action(session, state_machine)
        status_events = [event for event in events if event["event"] == "AGENT_STATUS_CHANGE"]
        alive_target = next(agent for agent in updated_session["agents"] if agent["id"] == 2)
        heal_events = [event for event in events if event["event"] == "AGENT_SKILL" and event["skill"] == "heal"]

        assert alive_target["status"] == "alive"
        assert heal_events
        assert status_events == []
    finally:
        agent_registry.clear_game(session["game_id"])


def test_witch_poison_can_eliminate_a_separate_target() -> None:
    state_machine, session = build_custom_runtime_session(
        "witch-poison",
        [
            {"id": 1, "role": "狼人", "camp": "狼人", "status": "alive"},
            {"id": 2, "role": "村民", "camp": "好人", "status": "alive"},
            {"id": 3, "role": "预言家", "camp": "好人", "status": "alive"},
            {"id": 4, "role": "女巫", "camp": "好人", "status": "alive"},
            {"id": 5, "role": "村民", "camp": "好人", "status": "alive"},
        ],
    )

    try:
        updated_session, events = run_night_action(session, state_machine)
        dead_ids = {agent["id"] for agent in updated_session["agents"] if agent["status"] == "dead"}
        status_events = [event for event in events if event["event"] == "AGENT_STATUS_CHANGE"]
        poison_events = [event for event in events if event["event"] == "AGENT_SKILL" and event["skill"] == "poison"]
        heal_events = [event for event in events if event["event"] == "AGENT_SKILL" and event["skill"] == "heal"]

        assert dead_ids == set()
        assert status_events == []
        assert poison_events == []
        assert heal_events
    finally:
        agent_registry.clear_game(session["game_id"])


def test_hunter_does_not_shoot_when_poisoned_at_night() -> None:
    state_machine, session = build_custom_runtime_session(
        "hunter-poisoned",
        [
            {"id": 1, "role": "狼人", "camp": "狼人", "status": "alive"},
            {"id": 2, "role": "猎人", "camp": "好人", "status": "alive"},
            {"id": 3, "role": "女巫", "camp": "好人", "status": "alive"},
            {"id": 4, "role": "村民", "camp": "好人", "status": "alive"},
        ],
    )

    original_registry = agent_registry

    class HunterPoisonAgent(StaticDecisionAgent):
        def __init__(self) -> None:
            super().__init__(vote_target_id=1)
            self.memory = StaticMemory()

        def observe_private_fact(self, fact: dict[str, object]) -> None:
            self.memory.private_facts.append(fact)

    class StaticNightAgent(StaticDecisionAgent):
        def __init__(self, *, skill: str | None = None, target_id: int | None = None) -> None:
            super().__init__(vote_target_id=1)
            self.memory = StaticMemory()
            self.skill = skill
            self.target_id = target_id

        def use_skill(self, _decision_input):
            return SkillDecision(skill=self.skill or "skip", target_id=self.target_id)

        def observe_private_fact(self, fact: dict[str, object]) -> None:
            self.memory.private_facts.append(fact)

    stub_registry = StubRegistry({
        1: StaticNightAgent(skill="kill", target_id=4),
        2: HunterPoisonAgent(),
        3: StaticNightAgent(skill="poison", target_id=2),
        4: StaticNightAgent(skill="skip", target_id=None),
    })

    try:
        from game_engine.actions import night as night_module

        night_module.agent_registry = stub_registry
        updated_session, events = run_night_action(session, state_machine)
    finally:
        from game_engine.actions import night as night_module

        night_module.agent_registry = original_registry

    hunter_snapshot = next(agent for agent in updated_session["agents"] if agent["id"] == 2)
    shot_events = [
        event for event in events
        if event["event"] == "AGENT_SKILL" and event["role"] == "猎人" and event["id"] == 2
    ]
    hunter_death_events = [
        event for event in events
        if event["event"] == "AGENT_STATUS_CHANGE" and event["id"] == 2
    ]

    assert hunter_snapshot["status"] == "dead"
    assert hunter_death_events == [{"event": "AGENT_STATUS_CHANGE", "id": 2, "status": "dead", "cause": "poison"}]
    assert shot_events == []


def test_hunter_shoots_after_night_death() -> None:
    state_machine, session = build_custom_runtime_session(
        "hunter-night-shot",
        [
            {"id": 1, "role": "狼人", "camp": "狼人", "status": "alive"},
            {"id": 2, "role": "猎人", "camp": "好人", "status": "alive"},
            {"id": 3, "role": "村民", "camp": "好人", "status": "alive"},
            {"id": 4, "role": "村民", "camp": "好人", "status": "alive"},
        ],
    )

    try:
        updated_session, events = run_night_action(session, state_machine)
        dead_ids = {agent["id"] for agent in updated_session["agents"] if agent["status"] == "dead"}
        shot_events = [event for event in events if event["event"] == "AGENT_SKILL" and event["role"] == "猎人"]
        hunter_death_events = [
            event for event in events
            if event["event"] == "AGENT_STATUS_CHANGE" and event["id"] == 2
        ]

        assert dead_ids == {2, 1}
        assert hunter_death_events == [{"event": "AGENT_STATUS_CHANGE", "id": 2, "status": "dead", "cause": "wolf_attack"}]
        assert shot_events
        assert updated_session["winner"] == "好人"
    finally:
        agent_registry.clear_game(session["game_id"])


def test_hunter_shoots_after_vote_death() -> None:
    state_machine, session = build_custom_runtime_session(
        "hunter-vote-shot",
        [
            {"id": 1, "role": "猎人", "camp": "好人", "status": "alive"},
            {"id": 2, "role": "村民", "camp": "好人", "status": "alive"},
            {"id": 3, "role": "狼人", "camp": "狼人", "status": "alive"},
        ],
    )
    session["phase"] = "day_speech"

    try:
        updated_session, events = run_voting_action(session, state_machine)
        dead_ids = {agent["id"] for agent in updated_session["agents"] if agent["status"] == "dead"}
        shot_events = [event for event in events if event["event"] == "AGENT_SKILL" and event["role"] == "猎人"]
        hunter_death_events = [
            event for event in events
            if event["event"] == "AGENT_STATUS_CHANGE" and event["id"] == 1
        ]

        assert dead_ids == {1, 2}
        assert hunter_death_events == [{"event": "AGENT_STATUS_CHANGE", "id": 1, "status": "dead", "cause": "vote_exile"}]
        assert shot_events
    finally:
        agent_registry.clear_game(session["game_id"])


def test_idiot_is_exiled_instead_of_dead_after_vote() -> None:
    state_machine, session = build_custom_runtime_session(
        "idiot-vote-exile",
        [
            {"id": 1, "role": "白痴", "camp": "好人", "status": "alive"},
            {"id": 2, "role": "狼人", "camp": "狼人", "status": "alive"},
            {"id": 3, "role": "村民", "camp": "好人", "status": "alive"},
        ],
    )
    session["phase"] = "day_speech"

    try:
        updated_session, events = run_voting_action(session, state_machine)
        idiot_snapshot = next(agent for agent in updated_session["agents"] if agent["id"] == 1)
        exile_events = [event for event in events if event["event"] == "AGENT_STATUS_CHANGE" and event["id"] == 1]
        shot_events = [event for event in events if event["event"] == "AGENT_SKILL" and event["role"] == "猎人"]

        assert idiot_snapshot["status"] == "exiled"
        assert exile_events == [{
            "event": "AGENT_STATUS_CHANGE",
            "id": 1,
            "status": "exiled",
            "role": "白痴",
            "revealed_role": "白痴",
            "can_vote": False,
            "can_speak": False,
            "is_alive": True,
            "special": "idiot_revealed",
        }]
        assert shot_events == []
    finally:
        agent_registry.clear_game(session["game_id"])


def test_exiled_idiot_still_counts_as_active_for_winner_calculation() -> None:
    state_machine = GameStateMachine()
    session = state_machine.create_initial_session(
        game_id="idiot-winner-active",
        agents=[
            {"id": 1, "role": "狼人", "camp": "狼人", "status": "alive"},
            {"id": 2, "role": "白痴", "camp": "好人", "status": "exiled"},
            {"id": 3, "role": "预言家", "camp": "好人", "status": "alive"},
        ],
    )

    assert state_machine.calculate_winner(session) is None


def test_exiled_idiot_keeps_good_camp_alive_until_wolves_are_cleared() -> None:
    state_machine = GameStateMachine()
    session = state_machine.create_initial_session(
        game_id="idiot-good-camp-win",
        agents=[
            {"id": 1, "role": "狼人", "camp": "狼人", "status": "dead"},
            {"id": 2, "role": "白痴", "camp": "好人", "status": "exiled"},
            {"id": 3, "role": "村民", "camp": "好人", "status": "dead"},
        ],
    )

    assert state_machine.calculate_winner(session) == "好人"


def test_phase_driven_executor_iter_game_streams_phase_batches() -> None:
    state_machine = GameStateMachine()
    executor = PhaseDrivenExecutor(state_machine)
    session = state_machine.create_initial_session(
        game_id="iter-game-stream",
        agents=[
            {"id": 1, "role": "狼人", "camp": "狼人", "status": "alive"},
            {"id": 2, "role": "村民", "camp": "好人", "status": "alive"},
            {"id": 3, "role": "预言家", "camp": "好人", "status": "alive"},
            {"id": 4, "role": "村民", "camp": "好人", "status": "alive"},
        ],
    )
    agent_registry.register_game_agents(session["game_id"], build_runtime_agents(session))

    try:
        streamed_batches = list(executor.iter_game(session))
    finally:
        agent_registry.clear_game(session["game_id"])

    assert streamed_batches
    batch_event_names = [[event["event"] for event in events] for _, events in streamed_batches]
    assert batch_event_names[0][0] == "PHASE_CHANGE"
    assert any("AGENT_SKILL" in names for names in batch_event_names)
    assert any("GAME_OVER" in names for names in batch_event_names)
    assert any(status == GameStatus.FINISHED for status, _ in [(streamed_session["status"], events) for streamed_session, events in streamed_batches])


def test_phase_driven_executor_iter_game_events_streams_individual_events() -> None:
    state_machine = GameStateMachine()
    executor = PhaseDrivenExecutor(state_machine)
    session = state_machine.create_initial_session(
        game_id="iter-game-events",
        agents=[
            {"id": 1, "role": "狼人", "camp": "狼人", "status": "alive"},
            {"id": 2, "role": "村民", "camp": "好人", "status": "alive"},
            {"id": 3, "role": "预言家", "camp": "好人", "status": "alive"},
            {"id": 4, "role": "村民", "camp": "好人", "status": "alive"},
        ],
    )
    agent_registry.register_game_agents(session["game_id"], build_runtime_agents(session))

    try:
        streamed_events = list(executor.iter_game_events(session))
    finally:
        agent_registry.clear_game(session["game_id"])

    assert streamed_events
    event_names = [event["event"] for _, event in streamed_events]
    assert event_names[0] == "PHASE_CHANGE"
    assert "AGENT_SKILL" in event_names
    assert "GAME_OVER" in event_names
    assert any(name == "AGENT_SPEAK" for name in event_names if name != "GAME_OVER") or "AGENT_SPEAK" not in event_names
    assert streamed_events[-1][0]["status"] == GameStatus.FINISHED


def test_phase_driven_executor_runs_multiple_rounds_until_finish() -> None:
    state_machine = GameStateMachine()
    executor = PhaseDrivenExecutor(state_machine)
    session = state_machine.create_initial_session(
        game_id="executor-multi-round",
        agents=[
            {"id": 1, "role": "狼人", "camp": "狼人", "status": "alive"},
            {"id": 2, "role": "村民", "camp": "好人", "status": "alive"},
            {"id": 3, "role": "预言家", "camp": "好人", "status": "alive"},
            {"id": 4, "role": "村民", "camp": "好人", "status": "alive"},
        ],
    )
    session = state_machine.advance_phase(session)
    session = state_machine.advance_phase(session)
    session = state_machine.advance_phase(session)
    agent_registry.register_game_agents(session["game_id"], build_runtime_agents(session))

    try:
        updated_session, events = executor.run(session)
    finally:
        agent_registry.clear_game(session["game_id"])

    assert updated_session["status"] == GameStatus.FINISHED
    assert updated_session["winner"] in {"好人", "狼人"}
    assert updated_session["round"] >= 2

    phase_events = [event for event in events if event["event"] == "PHASE_CHANGE"]
    phase_rounds = [
        ((event["phase"].value if hasattr(event["phase"], "value") else event["phase"]), event["round"])
        for event in phase_events
    ]
    assert phase_rounds[0] == ("night", 2)
    assert phase_rounds[-1][0] == "finished"
    assert phase_rounds[-1][1] >= 2
    event_names = [event["event"] for event in events]
    assert event_names.count("GAME_OVER") == 1
    assert any(name in event_names for name in {"AGENT_SPEAK", "AGENT_VOTE", "AGENT_SKILL"})


def test_phase_driven_executor_stops_on_terminal_night() -> None:
    state_machine = GameStateMachine()
    executor = PhaseDrivenExecutor(state_machine)
    session = state_machine.create_initial_session(
        game_id="executor-stop",
        agents=[
            {"id": 1, "role": "狼人", "camp": "狼人", "status": "alive"},
            {"id": 2, "role": "村民", "camp": "好人", "status": "alive"},
            {"id": 3, "role": "预言家", "camp": "好人", "status": "dead"},
        ],
    )
    agent_registry.register_game_agents(session["game_id"], build_runtime_agents(session))

    try:
        updated_session, events = executor.run(session)
    finally:
        agent_registry.clear_game(session["game_id"])

    assert updated_session["winner"] == "狼人"
    assert updated_session["status"] == GameStatus.FINISHED
    event_names = [event["event"] for event in events]
    assert "GAME_OVER" in event_names
    assert "AGENT_SPEAK" not in event_names
    assert "AGENT_VOTE" not in event_names


def test_real_model_path_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    client = LLMServiceClient()

    monkeypatch.setattr("llm_service.client.settings.llm_provider", "langchain_openai")
    monkeypatch.setattr("llm_service.client.settings.llm_api_key", "")
    monkeypatch.setattr("llm_service.client.ChatOpenAI", object())
    monkeypatch.setattr("llm_service.client.StrOutputParser", object())

    assert client._can_use_real_model() is False


def test_real_model_path_is_enabled_with_provider_and_key(monkeypatch: pytest.MonkeyPatch) -> None:
    client = LLMServiceClient()

    monkeypatch.setattr("llm_service.client.settings.llm_provider", "langchain_openai")
    monkeypatch.setattr("llm_service.client.settings.llm_api_key", "test-key")
    monkeypatch.setattr("llm_service.client.ChatOpenAI", object())
    monkeypatch.setattr("llm_service.client.StrOutputParser", object())

    assert client._can_use_real_model() is True


def test_speech_prompt_template_invocation_receives_all_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    state_machine, session = build_runtime_test_session("speech-template-vars")

    try:
        speaker_snapshot = next(agent for agent in session["agents"] if agent["status"] == "alive")
        speaker_agent = agent_registry.get_agent(session["game_id"], speaker_snapshot["id"])
        speech_input = speaker_agent.enrich_decision_input(
            "speech",
            build_agent_decision_input(
                session,
                speaker_snapshot,
                speaker_agent,
                legal_actions={"type": "speak", "allowed": True},
            ),
        )
        client = LLMServiceClient()

        monkeypatch.setattr("llm_service.client.settings.llm_provider", "langchain_openai")
        monkeypatch.setattr("llm_service.client.settings.llm_api_key", "test-key")

        class DummyParser:
            pass

        class DummyModel:
            def __ror__(self, other):
                return self

        class DummyChain:
            def __init__(self) -> None:
                self.received: dict[str, object] | None = None

            def __or__(self, _other):
                return self

            def invoke(self, payload: dict[str, object]) -> str:
                self.received = payload
                return '{"content":"测试发言"}'

        dummy_chain = DummyChain()

        class DummyTemplate:
            def __or__(self, _other):
                return dummy_chain

        monkeypatch.setattr("llm_service.client.ChatOpenAI", lambda **_kwargs: DummyModel())
        monkeypatch.setattr("llm_service.client.StrOutputParser", lambda: DummyParser())
        monkeypatch.setattr("llm_service.client.SPEECH_PROMPT_TEMPLATE", DummyTemplate())

        decision = client.generate_speech(speech_input)

        assert decision.content == "测试发言"
        assert dummy_chain.received is not None
        assert dummy_chain.received["role_instruction"]
        assert dummy_chain.received["action_guidance"]
        assert dummy_chain.received["payload"]
    finally:
        agent_registry.clear_game(session["game_id"])


    state_machine, session = build_runtime_test_session("speech-plain-text")

    try:
        speaker_snapshot = next(agent for agent in session["agents"] if agent["status"] == "alive")
        speaker_agent = agent_registry.get_agent(session["game_id"], speaker_snapshot["id"])
        speech_input = build_agent_decision_input(
            session,
            speaker_snapshot,
            speaker_agent,
            legal_actions={"type": "speak", "allowed": True},
        )
        client = LLMServiceClient()

        monkeypatch.setattr("llm_service.client.settings.llm_provider", "langchain_openai")
        monkeypatch.setattr("llm_service.client.settings.llm_api_key", "test-key")
        monkeypatch.setattr("llm_service.client.ChatOpenAI", object())
        monkeypatch.setattr("llm_service.client.StrOutputParser", object())
        monkeypatch.setattr(client, "_invoke_text_model", lambda *_args, **_kwargs: "我是 2 号，先听发言再判断。")

        decision = client.generate_speech(speech_input)

        assert decision.content == "我是 2 号，先听发言再判断。"
    finally:
        agent_registry.clear_game(session["game_id"])


def test_speech_generation_extracts_content_from_fenced_json_output(monkeypatch: pytest.MonkeyPatch) -> None:
    state_machine, session = build_runtime_test_session("speech-fenced-json")

    try:
        speaker_snapshot = next(agent for agent in session["agents"] if agent["status"] == "alive")
        speaker_agent = agent_registry.get_agent(session["game_id"], speaker_snapshot["id"])
        speech_input = build_agent_decision_input(
            session,
            speaker_snapshot,
            speaker_agent,
            legal_actions={"type": "speak", "allowed": True},
        )
        client = LLMServiceClient()

        monkeypatch.setattr("llm_service.client.settings.llm_provider", "langchain_openai")
        monkeypatch.setattr("llm_service.client.settings.llm_api_key", "test-key")
        monkeypatch.setattr("llm_service.client.ChatOpenAI", object())
        monkeypatch.setattr("llm_service.client.StrOutputParser", object())
        monkeypatch.setattr(
            client,
            "_invoke_text_model",
            lambda *_args, **_kwargs: '```json\n{"content":"我们已经投对了一个狼人，现在2号是狼人，大家请投票给2号。"}\n```',
        )

        decision = client.generate_speech(speech_input)

        assert decision.content == "我们已经投对了一个狼人，现在2号是狼人，大家请投票给2号。"
    finally:
        agent_registry.clear_game(session["game_id"])


def test_speech_generation_falls_back_when_model_output_is_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    state_machine, session = build_runtime_test_session("speech-empty")

    try:
        speaker_snapshot = next(agent for agent in session["agents"] if agent["status"] == "alive")
        speaker_agent = agent_registry.get_agent(session["game_id"], speaker_snapshot["id"])
        speech_input = build_agent_decision_input(
            session,
            speaker_snapshot,
            speaker_agent,
            legal_actions={"type": "speak", "allowed": True},
        )
        client = LLMServiceClient()

        monkeypatch.setattr("llm_service.client.settings.llm_provider", "langchain_openai")
        monkeypatch.setattr("llm_service.client.settings.llm_api_key", "test-key")
        monkeypatch.setattr("llm_service.client.ChatOpenAI", object())
        monkeypatch.setattr("llm_service.client.StrOutputParser", object())
        monkeypatch.setattr(client, "_invoke_text_model", lambda *_args, **_kwargs: "   ")

        decision = client.generate_speech(speech_input)

        assert decision.content
        assert 'agent_id' not in decision.content
        assert '输入：' not in decision.content
    finally:
        agent_registry.clear_game(session["game_id"])


def test_vote_generation_falls_back_when_model_output_is_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    state_machine, session = build_runtime_test_session("vote-fallback")

    try:
        voter_snapshot = next(agent for agent in session["agents"] if agent["status"] == "alive")
        voter_agent = agent_registry.get_agent(session["game_id"], voter_snapshot["id"])
        vote_input = build_agent_decision_input(
            session,
            voter_snapshot,
            voter_agent,
            legal_actions=build_vote_legal_actions(session, voter_snapshot),
        )
        client = LLMServiceClient()

        monkeypatch.setattr("llm_service.client.settings.llm_provider", "langchain_openai")
        monkeypatch.setattr("llm_service.client.settings.llm_api_key", "test-key")
        monkeypatch.setattr("llm_service.client.ChatOpenAI", object())
        monkeypatch.setattr("llm_service.client.StrOutputParser", object())
        monkeypatch.setattr(client, "_invoke_text_model", lambda *_args, **_kwargs: '{"target_id": 999}')

        decision = client.generate_vote(vote_input)

        assert isinstance(decision, VoteDecision)
        assert decision.target_id == vote_input.legal_actions["candidates"][0]
    finally:
        agent_registry.clear_game(session["game_id"])


def test_skill_generation_falls_back_when_model_output_is_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    state_machine, session = build_runtime_test_session("skill-fallback")

    try:
        seer_snapshot = next(agent for agent in session["agents"] if agent["role"] == "预言家")
        seer_agent = agent_registry.get_agent(session["game_id"], seer_snapshot["id"])
        skill_input = build_agent_decision_input(
            session,
            seer_snapshot,
            seer_agent,
            legal_actions=build_skill_legal_actions(session, seer_snapshot),
        )
        client = LLMServiceClient()

        monkeypatch.setattr("llm_service.client.settings.llm_provider", "langchain_openai")
        monkeypatch.setattr("llm_service.client.settings.llm_api_key", "test-key")
        monkeypatch.setattr("llm_service.client.ChatOpenAI", object())
        monkeypatch.setattr("llm_service.client.StrOutputParser", object())
        monkeypatch.setattr(client, "_invoke_text_model", lambda *_args, **_kwargs: '{"skill": "inspect", "target_id": 1}')

        decision = client.generate_skill(skill_input)

        assert isinstance(decision, SkillDecision)
        assert decision.skill == skill_input.legal_actions["skill"]
        assert decision.target_id == skill_input.legal_actions["targets"][0]
    finally:
        agent_registry.clear_game(session["game_id"])


def test_mock_speech_only_reacts_to_same_round_status_change() -> None:
    client = LLMServiceClient()
    speech_input = build_agent_decision_input(
        session={
            "game_id": "speech-round-check",
            "phase": "day_speech",
            "round": 2,
            "status": "running",
            "winner": None,
            "agents": [
                {"id": 1, "role": "村民", "camp": "好人", "status": "alive"},
                {"id": 2, "role": "村民", "camp": "好人", "status": "alive"},
            ],
            "public_events": [
                {"event": "AGENT_STATUS_CHANGE", "id": 4, "status": "dead", "round": 1},
            ],
        },
        agent_snapshot={"id": 1, "role": "村民", "camp": "好人", "status": "alive"},
        agent=build_agent(player_id=1, role="村民", camp="好人"),
        legal_actions={"type": "speak", "allowed": True},
    )

    decision = client.generate_speech(speech_input)

    assert "4号玩家已经出局" not in decision.content


    state_machine, session = build_runtime_test_session("role-aware-fallback")

    try:
        client = LLMServiceClient()
        werewolf_snapshot = next(agent for agent in session["agents"] if agent["role"] == "狼人")
        seer_snapshot = next(agent for agent in session["agents"] if agent["role"] == "预言家")
        werewolf_agent = agent_registry.get_agent(session["game_id"], werewolf_snapshot["id"])
        seer_agent = agent_registry.get_agent(session["game_id"], seer_snapshot["id"])

        werewolf_input = werewolf_agent.enrich_decision_input(
            "speech",
            build_agent_decision_input(session, werewolf_snapshot, werewolf_agent, legal_actions={"type": "speak", "allowed": True}),
        )
        seer_input = seer_agent.enrich_decision_input(
            "speech",
            build_agent_decision_input(session, seer_snapshot, seer_agent, legal_actions={"type": "speak", "allowed": True}),
        )

        werewolf_decision = client.generate_speech(werewolf_input)
        seer_decision = client.generate_speech(seer_input)

        assert werewolf_decision.content != seer_decision.content
        assert "查验" in seer_decision.content
    finally:
        agent_registry.clear_game(session["game_id"])


    state_machine = GameStateMachine()
    session = state_machine.create_initial_session(
        game_id="game-started-snapshot",
        agents=build_mock_agents(),
    )

    start_event = build_game_started_event(session)

    assert start_event["event"] == "GAME_STARTED"
    assert start_event["game_id"] == session["game_id"]
    assert start_event["agents"] == session["agents"]
    assert all(agent["status"] == "alive" for agent in start_event["agents"])



def test_skill_generation_accepts_valid_model_output(monkeypatch: pytest.MonkeyPatch) -> None:
    state_machine, session = build_runtime_test_session("skill-valid")

    try:
        seer_snapshot = next(agent for agent in session["agents"] if agent["role"] == "预言家")
        seer_agent = agent_registry.get_agent(session["game_id"], seer_snapshot["id"])
        skill_input = build_agent_decision_input(
            session,
            seer_snapshot,
            seer_agent,
            legal_actions=build_skill_legal_actions(session, seer_snapshot),
        )
        expected_target = skill_input.legal_actions["targets"][-1]
        client = LLMServiceClient()

        monkeypatch.setattr("llm_service.client.settings.llm_provider", "langchain_openai")
        monkeypatch.setattr("llm_service.client.settings.llm_api_key", "test-key")
        monkeypatch.setattr("llm_service.client.ChatOpenAI", object())
        monkeypatch.setattr("llm_service.client.StrOutputParser", object())
        monkeypatch.setattr(
            client,
            "_invoke_text_model",
            lambda *_args, **_kwargs: f'{{"skill": "inspect", "target_id": {expected_target}}}',
        )

        decision = client.generate_skill(skill_input)

        assert decision == SkillDecision(skill="inspect", target_id=expected_target)
    finally:
        agent_registry.clear_game(session["game_id"])



def test_real_model_vote_falls_back_on_invoke_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    state_machine, session = build_runtime_test_session("vote-invoke-error")

    try:
        voter_snapshot = next(agent for agent in session["agents"] if agent["status"] == "alive")
        voter_agent = agent_registry.get_agent(session["game_id"], voter_snapshot["id"])
        vote_input = build_agent_decision_input(
            session,
            voter_snapshot,
            voter_agent,
            legal_actions=build_vote_legal_actions(session, voter_snapshot),
        )
        client = LLMServiceClient()

        monkeypatch.setattr("llm_service.client.settings.llm_provider", "langchain_openai")
        monkeypatch.setattr("llm_service.client.settings.llm_api_key", "test-key")
        monkeypatch.setattr("llm_service.client.ChatOpenAI", object())
        monkeypatch.setattr("llm_service.client.StrOutputParser", object())

        def raise_error(*_args, **_kwargs):
            raise RuntimeError("provider failure")

        monkeypatch.setattr(client, "_invoke_text_model", raise_error)

        decision = client.generate_vote(vote_input)

        assert decision.target_id == vote_input.legal_actions["candidates"][0]
    finally:
        agent_registry.clear_game(session["game_id"])



def test_real_model_skill_falls_back_on_invoke_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    state_machine, session = build_runtime_test_session("skill-invoke-error")

    try:
        seer_snapshot = next(agent for agent in session["agents"] if agent["role"] == "预言家")
        seer_agent = agent_registry.get_agent(session["game_id"], seer_snapshot["id"])
        skill_input = build_agent_decision_input(
            session,
            seer_snapshot,
            seer_agent,
            legal_actions=build_skill_legal_actions(session, seer_snapshot),
        )
        client = LLMServiceClient()

        monkeypatch.setattr("llm_service.client.settings.llm_provider", "langchain_openai")
        monkeypatch.setattr("llm_service.client.settings.llm_api_key", "test-key")
        monkeypatch.setattr("llm_service.client.ChatOpenAI", object())
        monkeypatch.setattr("llm_service.client.StrOutputParser", object())

        def raise_error(*_args, **_kwargs):
            raise RuntimeError("provider failure")

        monkeypatch.setattr(client, "_invoke_text_model", raise_error)

        decision = client.generate_skill(skill_input)

        assert decision.skill == skill_input.legal_actions["skill"]
        assert decision.target_id == skill_input.legal_actions["targets"][0]
    finally:
        agent_registry.clear_game(session["game_id"])
