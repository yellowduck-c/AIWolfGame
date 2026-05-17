from __future__ import annotations

import json

from agent.state.schemas import AgentDecisionInput

try:
    from langchain_core.prompts import ChatPromptTemplate
except ModuleNotFoundError:
    ChatPromptTemplate = None


ACTION_INSTRUCTIONS = {
    "speech": [
        "请生成一句简短自然的中文发言。",
        "只输出 JSON 对象，不要输出额外解释、代码块或多余字段。",
        "仅输出 JSON：{{\"content\":\"...\"}}",
    ],
    "camp_chat": [
        "你现在需要向狼人同伴发送一句简短夜间私聊。",
        "只允许基于 public_state、private_state、camp_shared_state、derived_context 与 legal_actions 里的信息。",
        "不要输出公开发言，不要复述整个输入，不要输出分析过程。",
        "只输出 JSON 对象，不要输出额外解释、代码块或多余字段。",
        "仅输出 JSON：{{\"content\":\"...\"}}",
    ],
    "vote": [
        "你现在需要进行投票。",
        "只能从 legal_actions.candidates 中选择一个目标。",
        "只输出 JSON 对象，不要输出额外解释、代码块或多余字段。",
        "仅输出 JSON：{{\"target_id\":2}}",
    ],
    "skill": [
        "你现在需要使用技能。",
        "只能选择 legal_actions 中允许的 skill 与 target_id。",
        "优先参考 derived_context 中的高信号摘要，再结合原始状态字段做决定。",
        "如果你是狼人，并且 derived_context 或 camp_shared_state 已显示明确的统一击杀目标，优先执行这个共同目标，不要无故偏离。",
        "如果当前技能不需要目标，可输出 target_id 为 null。",
        "只输出 JSON 对象，不要输出额外解释、代码块或多余字段。",
        "仅输出 JSON：{{\"skill\":\"inspect\",\"target_id\":3}}",
    ],
}


SECTION_TITLES = {
    "global_rules": "【基础规则】",
    "role_layer": "【你的身份】",
    "action_layer": "【本次行动】",
    "derived_context": "【高信号摘要】",
    "output_contract": "【输出要求】",
    "input_payload": "【输入数据】",
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
            "derived_context": decision_input.derived_context,
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
        lines.append("倾向：" + " / ".join(behavior_tags))
    return "\n".join(line for line in lines if line.split("：", 1)[1])


def _build_action_guidance_instruction(decision_input: AgentDecisionInput) -> str:
    guidance = decision_input.specialization.get("action_guidance", {})
    if not guidance:
        return ""
    lines = []
    goal = guidance.get("goal")
    if goal:
        lines.append(f"当前行动目标：{goal}")
    tactics = guidance.get("tactics", [])
    if tactics:
        lines.append("可用策略：" + "；".join(tactics))
    style = guidance.get("style", [])
    if style:
        lines.append("行动风格：" + "、".join(style))
    constraints = guidance.get("constraints", [])
    if constraints:
        lines.append("行动约束：" + "；".join(constraints))
    return "\n".join(lines)


def _build_global_rules_instruction(_decision_input: AgentDecisionInput, action_type: str) -> str:
    rules = [
        "你是狼人杀游戏中的一名玩家。只基于提供给你的信息做决策，不要编造额外规则，不要输出分析过程。",
        "别把自己没真正拿到的技能结果、隐藏事件或私下观察说成已经坐实的事实；其余伪装、试探、摇摆和博弈都可以灵活发挥。",
    ]
    if action_type == "camp_chat":
        rules.append("夜间私聊仅面向狼人同伴，内容应短、明确、可执行，不要闲聊。")
    return "\n".join(rules)


def _build_derived_context_instruction(decision_input: AgentDecisionInput) -> str:
    if not decision_input.derived_context:
        return ""
    return json.dumps(
        decision_input.derived_context,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _format_section(title: str, content: str) -> str:
    if not content:
        return ""
    return f"{title}\n{content}"


def _build_output_contract(action_type: str) -> str:
    return "\n".join(ACTION_INSTRUCTIONS[action_type])


def _build_prompt(decision_input: AgentDecisionInput, action_type: str) -> str:
    payload = _dump_payload(decision_input)
    sections = [
        _format_section(SECTION_TITLES["global_rules"], _build_global_rules_instruction(decision_input, action_type)),
        _format_section(SECTION_TITLES["role_layer"], _build_role_instruction(decision_input)),
        _format_section(SECTION_TITLES["action_layer"], _build_action_guidance_instruction(decision_input)),
        _format_section(SECTION_TITLES["derived_context"], _build_derived_context_instruction(decision_input)),
        _format_section(SECTION_TITLES["output_contract"], _build_output_contract(action_type)),
        _format_section(SECTION_TITLES["input_payload"], payload),
    ]
    return "\n\n".join(section for section in sections if section)


def build_speech_prompt(decision_input: AgentDecisionInput) -> str:
    payload = _dump_payload(decision_input)
    derived_context = _build_derived_context_instruction(decision_input)
    if ChatPromptTemplate is None:
        return _build_prompt(decision_input, "speech")

    messages = SPEECH_PROMPT_TEMPLATE.format_messages(
        global_rules=_build_global_rules_instruction(decision_input, "speech"),
        role_instruction=_build_role_instruction(decision_input),
        action_guidance=_build_action_guidance_instruction(decision_input),
        derived_context=derived_context,
        output_contract=_build_output_contract("speech"),
        payload=payload,
    )
    return "\n".join(message.content for message in messages)


def build_camp_chat_prompt(decision_input: AgentDecisionInput) -> str:
    return _build_prompt(decision_input, "camp_chat")


def build_vote_prompt(decision_input: AgentDecisionInput) -> str:
    return _build_prompt(decision_input, "vote")


def build_skill_prompt(decision_input: AgentDecisionInput) -> str:
    return _build_prompt(decision_input, "skill")


SPEECH_PROMPT_TEMPLATE = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "{global_rules}",
        ),
        (
            "human",
            "【你的身份】\n{role_instruction}\n\n【本次行动】\n{action_guidance}\n\n【高信号摘要】\n{derived_context}\n\n【输出要求】\n{output_contract}\n\n【输入数据】\n{payload}",
        ),
    ]
) if ChatPromptTemplate is not None else None
