from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from agent.roles.role_profiles import GLOBAL_BASE_RULE, RoleActionGuidance, RoleProfile, get_role_profile
from agent.state.memory import AgentMemory
from agent.state.schemas import AgentDecisionInput, SkillDecision, SpeechDecision, StreamingSpeechDecision, VoteDecision

if TYPE_CHECKING:
    from llm_service.client import LLMServiceClient

ActionType = Literal["speech", "vote", "skill", "camp_chat"]


class BaseAgent:
    def __init__(
        self,
        player_id: int,
        role: str,
        camp: str,
        llm_client: LLMServiceClient | None = None,
        memory: AgentMemory | None = None,
    ) -> None:
        self.player_id = player_id
        self.role = role
        self.camp = camp
        self.llm_client = llm_client or self._build_llm_client()
        self.memory = memory or AgentMemory(identity=self._build_identity())

    def _build_llm_client(self) -> "LLMServiceClient":
        from llm_service.client import LLMServiceClient

        return LLMServiceClient()

    def _build_identity(self):
        from agent.state.memory import AgentIdentityMemory

        return AgentIdentityMemory(player_id=self.player_id, role=self.role, camp=self.camp)

    def get_role_profile(self) -> RoleProfile:
        return get_role_profile(self.role)

    def get_action_guidance(self, action_type: ActionType, profile: RoleProfile) -> RoleActionGuidance:
        if action_type == "speech":
            return profile.speech_guidance
        if action_type == "vote":
            return profile.vote_guidance
        if action_type == "camp_chat":
            return profile.camp_chat_guidance
        return profile.skill_guidance

    def _build_role_instruction(self, profile: RoleProfile) -> str:
        lines = [
            f"你的身份定位：{profile.identity}",
            f"你的阵营目标：{profile.objective}",
            f"你的信息公开原则：{profile.disclosure_policy}",
            f"你的协作风格：{profile.cooperation_style}",
        ]
        if profile.behavior_tags:
            lines.append("倾向：" + " / ".join(profile.behavior_tags))
        return "\n".join(lines)

    def _build_action_guidance_instruction(self, guidance: RoleActionGuidance) -> str:
        lines = [f"当前行动目标：{guidance.goal}"]
        if guidance.tactics:
            lines.append("可用策略：" + "；".join(guidance.tactics))
        if guidance.style:
            lines.append("行动风格：" + "、".join(guidance.style))
        if guidance.constraints:
            lines.append("行动约束：" + "；".join(guidance.constraints))
        return "\n".join(lines)

    def prepare_action_context(self, action_type: ActionType, decision_input: AgentDecisionInput) -> dict[str, Any]:
        return {}

    def enrich_decision_input(self, action_type: ActionType, decision_input: AgentDecisionInput) -> AgentDecisionInput:
        profile = self.get_role_profile()
        action_guidance = self.get_action_guidance(action_type, profile)
        specialization = dict(decision_input.specialization)
        specialization.update(
            {
                "role_profile": profile.to_prompt_payload(),
                "action_type": action_type,
                "action_guidance": action_guidance.to_prompt_payload(),
                "behavior_tags": list(profile.behavior_tags),
                "global_rules_instruction": GLOBAL_BASE_RULE,
                "role_instruction": self._build_role_instruction(profile),
                "action_guidance_instruction": self._build_action_guidance_instruction(action_guidance),
            }
        )
        specialization.update(self.prepare_action_context(action_type, decision_input))
        return AgentDecisionInput(
            agent_id=decision_input.agent_id,
            role=decision_input.role,
            camp=decision_input.camp,
            phase=decision_input.phase,
            round=decision_input.round,
            public_state=decision_input.public_state,
            private_state=decision_input.private_state,
            camp_shared_state=decision_input.camp_shared_state,
            memory_summary=decision_input.memory_summary,
            legal_actions=decision_input.legal_actions,
            derived_context=decision_input.derived_context,
            specialization=specialization,
        )

    def validate_or_normalize_result(self, action_type: ActionType, result: Any) -> Any:
        return result

    def observe_public_event(self, event: dict[str, Any]) -> None:
        self.memory.record_public_observation(event)

    def observe_private_fact(self, fact: dict[str, Any]) -> None:
        self.memory.record_private_fact(fact)

    def speak(self, decision_input: AgentDecisionInput) -> SpeechDecision:
        enriched_input = self.enrich_decision_input("speech", decision_input)
        decision = self.llm_client.generate_speech(enriched_input)
        decision = self.validate_or_normalize_result("speech", decision)
        self.memory.record_speech(decision.content)
        return decision

    def speak_streaming(self, decision_input: AgentDecisionInput) -> StreamingSpeechDecision:
        enriched_input = self.enrich_decision_input("speech", decision_input)
        decision = self.llm_client.generate_streaming_speech(enriched_input)
        decision = self.validate_or_normalize_result("speech", decision)
        self.memory.record_speech(decision.content)
        return decision

    def vote(self, decision_input: AgentDecisionInput) -> VoteDecision:
        enriched_input = self.enrich_decision_input("vote", decision_input)
        decision = self.llm_client.generate_vote(enriched_input)
        decision = self.validate_or_normalize_result("vote", decision)
        self.memory.record_vote(decision.target_id)
        return decision

    def use_skill(self, decision_input: AgentDecisionInput) -> SkillDecision:
        enriched_input = self.enrich_decision_input("skill", decision_input)
        decision = self.llm_client.generate_skill(enriched_input)
        decision = self.validate_or_normalize_result("skill", decision)
        self.memory.record_skill({"skill": decision.skill, "target_id": decision.target_id})
        return decision

    def camp_chat(self, decision_input: AgentDecisionInput) -> str | None:
        if self.role != "狼人" or not decision_input.legal_actions.get("allowed", False):
            return None
        enriched_input = self.enrich_decision_input("camp_chat", decision_input)
        content = self.llm_client.generate_camp_chat(enriched_input)
        content = self.validate_or_normalize_result("camp_chat", content)
        if not isinstance(content, str):
            return None
        normalized = content.strip()
        return normalized or None
