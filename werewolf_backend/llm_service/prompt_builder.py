from __future__ import annotations

import json

from agent.state.schemas import AgentDecisionInput

try:
    from langchain_core.prompts import ChatPromptTemplate
except ModuleNotFoundError:
    ChatPromptTemplate = None


PROMPT_BASE_INSTRUCTION = "你是狼人杀游戏中的一名玩家。只基于提供给你的信息做决策，不要编造额外规则，不要输出分析过程。"

ACTION_INSTRUCTIONS = {
    "speech": [
        "请生成一句简短自然的中文发言。",
        "仅输出 JSON：{{\"content\":\"...\"}}",
    ],
    "vote": [
        "你现在需要进行投票。",
        "只能从 legal_actions.candidates 中选择一个目标。",
        "仅输出 JSON：{{\"target_id\":2}}",
    ],
    "skill": [
        "你现在需要使用技能。",
        "只能选择 legal_actions 中允许的 skill 与 target_id。",
        "如果当前技能不需要目标，可输出 target_id 为 null。",
        "仅输出 JSON：{{\"skill\":\"inspect\",\"target_id\":3}}",
    ],
}


def _dump_payload(decision_input: AgentDecisionInput) -> str:
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
            "specialization": decision_input.specialization,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _build_role_instruction(decision_input: AgentDecisionInput) -> str:
    role_profile = decision_input.specialization.get("role_profile", {})
    if not role_profile:
        return ""
    lines = [
        f"你的身份定位：{role_profile.get('identity', '')}",
        f"你的阵营目标：{role_profile.get('objective', '')}",
        f"你的信息公开原则：{role_profile.get('disclosure_policy', '')}",
        f"你的协作风格：{role_profile.get('cooperation_style', '')}",
    ]
    behavior_tags = role_profile.get("behavior_tags", [])
    if behavior_tags:
        lines.append(f"行为标签：{', '.join(behavior_tags)}")
    return "\n".join(line for line in lines if line.split("：", 1)[1])


def _build_action_guidance_instruction(decision_input: AgentDecisionInput) -> str:
    guidance = decision_input.specialization.get("action_guidance", {})
    if not guidance:
        return ""
    lines = []
    goal = guidance.get("goal")
    if goal:
        lines.append(f"当前行动目标：{goal}")
    constraints = guidance.get("constraints", [])
    if constraints:
        lines.append("行动约束：" + "；".join(constraints))
    priorities = guidance.get("priorities", [])
    if priorities:
        lines.append("行动优先级：" + "；".join(priorities))
    style = guidance.get("style", [])
    if style:
        lines.append("表达/决策风格：" + "、".join(style))
    return "\n".join(lines)


def _build_prompt(decision_input: AgentDecisionInput, action_type: str) -> str:
    payload = _dump_payload(decision_input)
    sections = [
        PROMPT_BASE_INSTRUCTION,
        _build_role_instruction(decision_input),
        _build_action_guidance_instruction(decision_input),
        *ACTION_INSTRUCTIONS[action_type],
        f"输入：{payload}",
    ]
    return "\n".join(section for section in sections if section)


def build_speech_prompt(decision_input: AgentDecisionInput) -> str:
    payload = _dump_payload(decision_input)
    if ChatPromptTemplate is None:
        return _build_prompt(decision_input, "speech")

    messages = SPEECH_PROMPT_TEMPLATE.format_messages(
        role_instruction=_build_role_instruction(decision_input),
        action_guidance=_build_action_guidance_instruction(decision_input),
        payload=payload,
    )
    return "\n".join(message.content for message in messages)


def build_vote_prompt(decision_input: AgentDecisionInput) -> str:
    return _build_prompt(decision_input, "vote")


def build_skill_prompt(decision_input: AgentDecisionInput) -> str:
    return _build_prompt(decision_input, "skill")


SPEECH_PROMPT_TEMPLATE = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            PROMPT_BASE_INSTRUCTION,
        ),
        (
            "human",
            "{role_instruction}\n{action_guidance}\n请生成一句简短自然的中文发言。仅输出 JSON：{{\"content\":\"...\"}}\n输入：{payload}",
        ),
    ]
) if ChatPromptTemplate is not None else None
