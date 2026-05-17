from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable

from agent.state.schemas import AgentDecisionInput, SkillDecision, SpeechDecision, StreamingSpeechDecision, VoteDecision
from config import settings
from llm_service.prompt_builder import (
    SPEECH_PROMPT_TEMPLATE,
    build_camp_chat_prompt,
    build_skill_prompt,
    build_speech_prompt,
    build_vote_prompt,
)

try:
    from langchain_core.output_parsers import StrOutputParser
    from langchain_openai import ChatOpenAI
except ModuleNotFoundError:
    StrOutputParser = None
    ChatOpenAI = None

logger = logging.getLogger(__name__)


class LLMServiceClient:
    def generate_speech(self, decision_input: AgentDecisionInput) -> SpeechDecision:
        real_model_available = self._can_use_real_model()
        logger.info(
            "llm mode check operation=speech agent_id=%s role=%s provider=%s model=%s real_model_available=%s",
            decision_input.agent_id,
            decision_input.role,
            settings.llm_provider,
            settings.llm_model,
            real_model_available,
        )
        if real_model_available:
            decision = self._try_generate_real_speech(decision_input)
            if decision is not None:
                logger.info(
                    "llm decision generated mode=real operation=speech agent_id=%s role=%s",
                    decision_input.agent_id,
                    decision_input.role,
                )
                return decision
        logger.info(
            "llm decision fallback mode=mock operation=speech agent_id=%s role=%s",
            decision_input.agent_id,
            decision_input.role,
        )
        return self._generate_mock_speech(decision_input)

    def generate_streaming_speech(self, decision_input: AgentDecisionInput) -> StreamingSpeechDecision:
        decision = self.generate_speech(decision_input)
        chunks = [chunk for chunk in decision.content.split("，") if chunk]
        if not chunks:
            chunks = [decision.content]
        return StreamingSpeechDecision(content=decision.content, chunks=chunks)

    def generate_camp_chat(self, decision_input: AgentDecisionInput) -> str | None:
        real_model_available = self._can_use_real_model()
        logger.info(
            "llm mode check operation=camp_chat agent_id=%s role=%s provider=%s model=%s real_model_available=%s",
            decision_input.agent_id,
            decision_input.role,
            settings.llm_provider,
            settings.llm_model,
            real_model_available,
        )
        if real_model_available:
            content = self._try_generate_real_camp_chat(decision_input)
            if content is not None:
                logger.info(
                    "llm decision generated mode=real operation=camp_chat agent_id=%s role=%s",
                    decision_input.agent_id,
                    decision_input.role,
                )
                return content
        logger.info(
            "llm decision fallback mode=mock operation=camp_chat agent_id=%s role=%s",
            decision_input.agent_id,
            decision_input.role,
        )
        return self._generate_mock_camp_chat(decision_input)

    def generate_vote(self, decision_input: AgentDecisionInput) -> VoteDecision:
        real_model_available = self._can_use_real_model()
        logger.info(
            "llm mode check operation=vote agent_id=%s role=%s provider=%s model=%s real_model_available=%s",
            decision_input.agent_id,
            decision_input.role,
            settings.llm_provider,
            settings.llm_model,
            real_model_available,
        )
        if real_model_available:
            decision = self._try_generate_real_vote(decision_input)
            if decision is not None:
                logger.info(
                    "llm decision generated mode=real operation=vote agent_id=%s role=%s",
                    decision_input.agent_id,
                    decision_input.role,
                )
                return decision
        logger.info(
            "llm decision fallback mode=mock operation=vote agent_id=%s role=%s",
            decision_input.agent_id,
            decision_input.role,
        )
        return self._generate_mock_vote(decision_input)

    def generate_skill(self, decision_input: AgentDecisionInput) -> SkillDecision:
        real_model_available = self._can_use_real_model()
        logger.info(
            "llm mode check operation=skill agent_id=%s role=%s provider=%s model=%s real_model_available=%s",
            decision_input.agent_id,
            decision_input.role,
            settings.llm_provider,
            settings.llm_model,
            real_model_available,
        )
        if real_model_available:
            decision = self._try_generate_real_skill(decision_input)
            if decision is not None:
                logger.info(
                    "llm decision generated mode=real operation=skill agent_id=%s role=%s",
                    decision_input.agent_id,
                    decision_input.role,
                )
                return decision
        logger.info(
            "llm decision fallback mode=mock operation=skill agent_id=%s role=%s",
            decision_input.agent_id,
            decision_input.role,
        )
        return self._generate_mock_skill(decision_input)

    def _try_generate_real_speech(self, decision_input: AgentDecisionInput) -> SpeechDecision | None:
        try:
            raw_output = self._invoke_text_model(decision_input, builder=build_speech_prompt, operation="speech")
        except Exception as error:
            logger.warning(
                "llm invocation failed operation=speech agent_id=%s role=%s provider=%s model=%s error=%s",
                decision_input.agent_id,
                decision_input.role,
                settings.llm_provider,
                settings.llm_model,
                error,
            )
            return None
        decision = self._parse_speech_decision(raw_output)
        if decision is not None and decision.content.strip():
            return decision
        logger.warning(
            "llm parse failed operation=speech agent_id=%s role=%s reason=empty_or_invalid_output",
            decision_input.agent_id,
            decision_input.role,
        )
        return None

    def _try_generate_real_vote(self, decision_input: AgentDecisionInput) -> VoteDecision | None:
        try:
            raw_output = self._invoke_text_model(decision_input, builder=build_vote_prompt, operation="vote")
        except Exception as error:
            logger.warning(
                "llm invocation failed operation=vote agent_id=%s role=%s provider=%s model=%s error=%s",
                decision_input.agent_id,
                decision_input.role,
                settings.llm_provider,
                settings.llm_model,
                error,
            )
            return None
        decision = self._parse_vote_decision(raw_output, decision_input)
        if decision is not None:
            return decision
        logger.warning(
            "llm parse failed operation=vote agent_id=%s role=%s reason=invalid_target",
            decision_input.agent_id,
            decision_input.role,
        )
        return None

    def _try_generate_real_camp_chat(self, decision_input: AgentDecisionInput) -> str | None:
        try:
            raw_output = self._invoke_text_model(decision_input, builder=build_camp_chat_prompt, operation="camp_chat")
        except Exception as error:
            logger.warning(
                "llm invocation failed operation=camp_chat agent_id=%s role=%s provider=%s model=%s error=%s",
                decision_input.agent_id,
                decision_input.role,
                settings.llm_provider,
                settings.llm_model,
                error,
            )
            return None
        content = self._parse_text_content(raw_output)
        if content is not None:
            return content
        logger.warning(
            "llm parse failed operation=camp_chat agent_id=%s role=%s reason=empty_or_invalid_output",
            decision_input.agent_id,
            decision_input.role,
        )
        return None

    def _try_generate_real_skill(self, decision_input: AgentDecisionInput) -> SkillDecision | None:
        try:
            raw_output = self._invoke_text_model(decision_input, builder=build_skill_prompt, operation="skill")
        except Exception as error:
            logger.warning(
                "llm invocation failed operation=skill agent_id=%s role=%s provider=%s model=%s error=%s",
                decision_input.agent_id,
                decision_input.role,
                settings.llm_provider,
                settings.llm_model,
                error,
            )
            return None
        decision = self._parse_skill_decision(raw_output, decision_input)
        if decision is not None:
            return decision
        logger.warning(
            "llm parse failed operation=skill agent_id=%s role=%s reason=invalid_skill_choice",
            decision_input.agent_id,
            decision_input.role,
        )
        return None

    def _can_use_real_model(self) -> bool:
        can_use = (
            settings.llm_provider == "langchain_openai"
            and ChatOpenAI is not None
            and StrOutputParser is not None
            and bool(settings.llm_api_key.strip())
        )
        if not can_use:
            logger.info(
                "llm real model unavailable provider=%s has_chat_openai=%s has_parser=%s has_api_key=%s",
                settings.llm_provider,
                ChatOpenAI is not None,
                StrOutputParser is not None,
                bool(settings.llm_api_key.strip()),
            )
        return can_use

    def _invoke_text_model(
        self,
        decision_input: AgentDecisionInput,
        builder: Callable[[AgentDecisionInput], str],
        operation: str,
    ) -> str:
        prompt = builder(decision_input)
        logger.info(
            "llm invocation start operation=%s agent_id=%s role=%s provider=%s model=%s",
            operation,
            decision_input.agent_id,
            decision_input.role,
            settings.llm_provider,
            settings.llm_model,
        )
        started_at = time.perf_counter()
        model = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url or None,
            temperature=settings.llm_temperature,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )
        if builder is build_speech_prompt and SPEECH_PROMPT_TEMPLATE is not None:
            chain = SPEECH_PROMPT_TEMPLATE | model | StrOutputParser()
            result = chain.invoke(
                {
                    "global_rules": decision_input.specialization.get("global_rules_instruction", ""),
                    "role_instruction": decision_input.specialization.get("role_instruction", ""),
                    "action_guidance": decision_input.specialization.get("action_guidance_instruction", ""),
                    "derived_context": (
                        json.dumps(
                            decision_input.derived_context,
                            ensure_ascii=False,
                            separators=(",", ":"),
                        )
                        if decision_input.derived_context
                        else ""
                    ),
                    "output_contract": "\n".join([
                        "请生成一句简短自然的中文发言。",
                        "只输出 JSON 对象，不要输出额外解释、代码块或多余字段。",
                        "仅输出 JSON：{\"content\":\"...\"}",
                    ]),
                    "payload": self._build_payload_text(decision_input),
                }
            ).strip()
        else:
            result = (model | StrOutputParser()).invoke(prompt).strip()
        logger.info(
            "llm invocation success operation=%s agent_id=%s role=%s provider=%s model=%s duration_ms=%.2f output_chars=%s",
            operation,
            decision_input.agent_id,
            decision_input.role,
            settings.llm_provider,
            settings.llm_model,
            (time.perf_counter() - started_at) * 1000,
            len(result),
        )
        return result

    def _build_payload_text(self, decision_input: AgentDecisionInput) -> str:
        return json.dumps(
            {
                "agent_id": decision_input.agent_id,
                "role": decision_input.role,
                "camp": decision_input.camp,
                "phase": decision_input.phase,
                "round": decision_input.round,
                "public_state": decision_input.public_state,
                "private_state": decision_input.private_state,
                "camp_shared_state": decision_input.camp_shared_state,
                "memory_summary": decision_input.memory_summary,
                "legal_actions": decision_input.legal_actions,
                "derived_context": decision_input.derived_context,
                "specialization": decision_input.specialization,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )

    def _parse_json_object(self, raw_output: str) -> dict[str, object] | None:
        try:
            parsed = json.loads(raw_output)
        except json.JSONDecodeError:
            return None
        if not isinstance(parsed, dict):
            return None
        return parsed

    def _parse_speech_decision(self, raw_output: str) -> SpeechDecision | None:
        content = self._parse_text_content(raw_output)
        if content is None:
            return None
        return SpeechDecision(content=content)

    def _parse_text_content(self, raw_output: str) -> str | None:
        parsed = self._parse_json_object(raw_output)
        if parsed is not None:
            content = parsed.get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()
            return None
        text = raw_output.strip()
        if not text:
            return None
        if text.startswith("```"):
            lines = text.splitlines()
            if lines:
                lines = lines[1:]
            while lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            fenced_text = "\n".join(lines).strip()
            parsed_fenced = self._parse_json_object(fenced_text)
            if parsed_fenced is not None:
                content = parsed_fenced.get("content")
                if isinstance(content, str) and content.strip():
                    return content.strip()
                return None
            text = fenced_text
        if text.startswith("输入：") or '"agent_id"' in text or '"public_state"' in text or '"legal_actions"' in text:
            return None
        return text

    def _parse_vote_decision(self, raw_output: str, decision_input: AgentDecisionInput) -> VoteDecision | None:
        parsed = self._parse_json_object(raw_output)
        if parsed is None:
            return None
        target_id = parsed.get("target_id")
        candidates = decision_input.legal_actions.get("candidates", [])
        if not isinstance(target_id, int) or target_id not in candidates:
            return None
        return VoteDecision(target_id=target_id)

    def _parse_skill_decision(self, raw_output: str, decision_input: AgentDecisionInput) -> SkillDecision | None:
        parsed = self._parse_json_object(raw_output)
        if parsed is None:
            return None
        skill = parsed.get("skill")
        target_id = parsed.get("target_id")
        if not isinstance(skill, str):
            return None
        if not self._is_valid_skill_choice(skill, target_id, decision_input):
            return None
        return SkillDecision(skill=skill, target_id=target_id)

    def _is_valid_skill_choice(self, skill: str, target_id: object, decision_input: AgentDecisionInput) -> bool:
        legal_actions = decision_input.legal_actions
        if not legal_actions.get("allowed", False):
            return False

        if decision_input.role == "女巫":
            can_heal = bool(legal_actions.get("can_heal"))
            can_poison = bool(legal_actions.get("can_poison"))
            wolf_target_id = legal_actions.get("wolf_target_id")
            if skill == "heal":
                return can_heal and target_id == wolf_target_id
            if skill == "poison":
                return can_poison and target_id in legal_actions.get("targets", [])
            return skill == "skip" and target_id is None

        if decision_input.role == "猎人":
            return skill == legal_actions.get("skill") and target_id in legal_actions.get("targets", [])

        expected_skill = legal_actions.get("skill")
        if skill != expected_skill:
            return False
        if target_id is None:
            return False
        return target_id in legal_actions.get("targets", [])

    def _generate_mock_vote(self, decision_input: AgentDecisionInput) -> VoteDecision:
        candidates = decision_input.legal_actions.get("candidates", [])
        target_id = candidates[0] if candidates else decision_input.agent_id
        return VoteDecision(target_id=target_id)

    def _generate_mock_skill(self, decision_input: AgentDecisionInput) -> SkillDecision:
        role = decision_input.role
        legal_actions = decision_input.legal_actions
        if role == "女巫":
            if legal_actions.get("can_heal"):
                return SkillDecision(skill="heal", target_id=legal_actions.get("wolf_target_id"))
            if legal_actions.get("can_poison"):
                targets = legal_actions.get("targets", [])
                target_id = targets[0] if targets else None
                return SkillDecision(skill="poison", target_id=target_id)
            return SkillDecision(skill="skip", target_id=None)

        targets = legal_actions.get("targets", [])
        target_id = targets[0] if targets else None
        skill = legal_actions.get("skill") or "default"
        return SkillDecision(skill=skill, target_id=target_id)

    def _generate_mock_camp_chat(self, decision_input: AgentDecisionInput) -> str | None:
        if decision_input.role != "狼人" or not decision_input.legal_actions.get("allowed", False):
            return None
        targets = decision_input.legal_actions.get("targets", [])
        if not targets:
            return "今晚先别乱动，我这边没有合适目标。"
        target_id = targets[0]
        teammates = decision_input.camp_shared_state.get("teammates", [])
        if teammates:
            return f"我建议今晚优先击杀{target_id}号，大家尽量统一票型。"
        return f"今晚我倾向击杀{target_id}号。"

    def _generate_mock_speech(self, decision_input: AgentDecisionInput) -> SpeechDecision:
        public_events = decision_input.public_state.get("public_events", [])
        recent_status = next(
            (
                event for event in reversed(public_events)
                if event.get("event") == "AGENT_STATUS_CHANGE"
            ),
            None,
        )
        current_round = decision_input.round
        if recent_status is not None and recent_status.get("round") == current_round:
            content = f"{recent_status['id']}号玩家已经出局，我会结合这个结果重新判断场上的身份。"
        elif decision_input.role == "狼人":
            content = "我先听大家怎么聊，再看谁的发言最像在带节奏。"
        elif decision_input.role == "预言家":
            content = "我会结合查验线索和场上的发言，优先判断真正可疑的人。"
        elif decision_input.role == "女巫":
            content = "这一轮我会更关注谁在借机冲票，先把信息听完整。"
        elif decision_input.role == "猎人":
            content = "我现在更在意谁的立场反复横跳，票型出来后会更清楚。"
        else:
            content = "我先按公开发言梳理可疑点，再决定这一轮要投谁。"
        return SpeechDecision(content=content)
