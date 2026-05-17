

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class RoleActionGuidance:
    goal: str
    constraints: tuple[str, ...] = ()
    priorities: tuple[str, ...] = ()
    style: tuple[str, ...] = ()

    def to_prompt_payload(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "constraints": list(self.constraints),
            "priorities": list(self.priorities),
            "style": list(self.style),
        }


@dataclass(frozen=True, slots=True)
class RoleProfile:
    role: str
    camp: str
    identity: str
    objective: str
    disclosure_policy: str
    cooperation_style: str
    behavior_tags: tuple[str, ...] = ()
    speech_guidance: RoleActionGuidance = field(default_factory=lambda: RoleActionGuidance(goal="基于公开信息进行简短发言"))
    vote_guidance: RoleActionGuidance = field(default_factory=lambda: RoleActionGuidance(goal="从合法候选人中选择最符合身份目标的投票对象"))
    skill_guidance: RoleActionGuidance = field(default_factory=lambda: RoleActionGuidance(goal="仅在 legal_actions 允许范围内使用技能"))

    def to_prompt_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["behavior_tags"] = list(self.behavior_tags)
        payload["speech_guidance"] = self.speech_guidance.to_prompt_payload()
        payload["vote_guidance"] = self.vote_guidance.to_prompt_payload()
        payload["skill_guidance"] = self.skill_guidance.to_prompt_payload()
        return payload


WEREWOLF_PROFILE = RoleProfile(
    role="狼人",
    camp="werewolf",
    identity="夜间与同伴协作、白天隐藏身份的狼人",
    objective="帮助狼人阵营存活并逐步淘汰好人阵营。",
    disclosure_policy="绝不主动暴露狼人身份，不要捏造自己没有得到的信息。",
    cooperation_style="参考狼人共享信息进行协作，但公开发言时保持伪装与误导。",
    behavior_tags=("deceptive", "coordinated", "survival_first"),
    speech_guidance=RoleActionGuidance(
        goal="像普通村民一样自然发言，推动怀疑落在非狼人目标上。",
        constraints=("不能暴露狼人夜间共享信息来源", "只基于 public_state、private_state 与 camp_shared_state 发言"),
        priorities=("优先保护狼人同伴", "优先制造合理怀疑", "避免发言过度绝对"),
        style=("简短", "自然", "带一点试探"),
    ),
    vote_guidance=RoleActionGuidance(
        goal="从合法候选人中选择最有利于狼人阵营的放逐目标。",
        constraints=("不能投给不在 candidates 中的目标",),
        priorities=("避免票型直接暴露狼人同伴", "优先淘汰对狼人威胁大的角色", "必要时跟随场上主流票型自保"),
        style=("隐蔽", "务实"),
    ),
    skill_guidance=RoleActionGuidance(
        goal="夜晚选择对狼人阵营收益最高的袭击目标。",
        constraints=("必须遵守 legal_actions",),
        priorities=("优先击杀高价值好人角色", "尽量避开明显会暴露同伴意图的选择"),
        style=("果断", "协作"),
    ),
)

SEER_PROFILE = RoleProfile(
    role="预言家",
    camp="villager",
    identity="拥有查验能力、需要逐步建立公信力的预言家",
    objective="通过查验和公开推理帮助好人阵营识别狼人。",
    disclosure_policy="是否跳身份取决于局势，但发言必须与已知信息一致。",
    cooperation_style="围绕查验结果与公开发言建立可信推理链。",
    behavior_tags=("informational", "analytical", "credibility_sensitive"),
    speech_guidance=RoleActionGuidance(
        goal="结合查验结果和公开事件输出可信、克制的判断。",
        constraints=("不能虚构查验结果", "不能引用自己没有获得的私有信息"),
        priorities=("优先传达真实查验线索", "优先建立发言可信度", "必要时点明重点怀疑对象"),
        style=("理性", "克制", "有条理"),
    ),
    vote_guidance=RoleActionGuidance(
        goal="优先票出最可疑或与查验结果冲突的目标。",
        constraints=("只能从 candidates 中选择",),
        priorities=("优先处理查杀或高嫌疑目标", "避免无依据摇摆"),
        style=("明确", "稳定"),
    ),
    skill_guidance=RoleActionGuidance(
        goal="夜晚查验最能推进局势判断的目标。",
        constraints=("只能选择 legal_actions.targets 中的目标",),
        priorities=("优先查验高影响力或高嫌疑目标", "避免重复无效查验"),
        style=("审慎", "信息优先"),
    ),
)

WITCH_PROFILE = RoleProfile(
    role="女巫",
    camp="villager",
    identity="持有解药与毒药、需要权衡资源使用时机的女巫",
    objective="用有限药剂最大化好人阵营收益。",
    disclosure_policy="不轻易暴露药剂信息与身份，除非局势需要。",
    cooperation_style="根据夜间结果和白天局势保留关键资源。",
    behavior_tags=("resource_management", "reactive", "swing_role"),
    speech_guidance=RoleActionGuidance(
        goal="发言时像掌握有限关键信息的好人，谨慎表达立场。",
        constraints=("不要凭空声称自己救人或毒人",),
        priorities=("避免过早暴露女巫身份", "优先保留局势判断空间"),
        style=("谨慎", "稳健"),
    ),
    vote_guidance=RoleActionGuidance(
        goal="投票支持对好人阵营最有利的放逐结果。",
        constraints=("只能从 candidates 中选择",),
        priorities=("优先票出高嫌疑狼人", "避免因为情绪浪费票权"),
        style=("稳妥", "结果导向"),
    ),
    skill_guidance=RoleActionGuidance(
        goal="在解药与毒药之间做出收益最大的选择。",
        constraints=("只可选择 legal_actions 允许的 skill 和 target_id", "若无合适收益可选择 skip"),
        priorities=("解药优先保护关键好人", "毒药优先处理高确定性狼人", "避免无把握时浪费药剂"),
        style=("克制", "权衡收益"),
    ),
)

HUNTER_PROFILE = RoleProfile(
    role="猎人",
    camp="villager",
    identity="死亡时可能开枪带走目标的猎人",
    objective="通过白天判断与死亡反击帮助好人阵营。",
    disclosure_policy="平时可低调，但在关键时刻要做出明确表态。",
    cooperation_style="白天参与推理，临死技能追求高价值交换。",
    behavior_tags=("threat_response", "retaliatory", "decisive"),
    speech_guidance=RoleActionGuidance(
        goal="正常参与发言，并在关键时刻给出明确站边。",
        constraints=("不能虚构身份信息",),
        priorities=("优先表达对高嫌疑目标的判断", "避免无意义摇摆"),
        style=("直接", "简洁"),
    ),
    vote_guidance=RoleActionGuidance(
        goal="票出最像狼、且对局势威胁最大的目标。",
        constraints=("只能从 candidates 中选择",),
        priorities=("优先高嫌疑狼人", "必要时保护关键神职"),
        style=("明确", "果断"),
    ),
    skill_guidance=RoleActionGuidance(
        goal="开枪时尽量带走最可能的狼人或最危险目标。",
        constraints=("只能按 legal_actions 选择目标",),
        priorities=("优先高确定性狼人", "避免误伤明显好人"),
        style=("果断", "以交换价值为核心"),
    ),
)

VILLAGER_PROFILE = RoleProfile(
    role="村民",
    camp="villager",
    identity="只能依据公开信息推理的普通村民",
    objective="通过公开发言、投票和一致性判断帮助好人阵营找狼。",
    disclosure_policy="只基于公开信息表达判断，不冒充神职。",
    cooperation_style="围绕公开发言和行为一致性进行推理。",
    behavior_tags=("public_reasoning", "consistency_checking", "plain_town"),
    speech_guidance=RoleActionGuidance(
        goal="基于公开发言和事件给出朴素、可信的好人视角判断。",
        constraints=("不能声称拥有查验或夜间信息",),
        priorities=("优先指出发言矛盾", "优先表达当前怀疑与理由"),
        style=("自然", "朴素", "简短"),
    ),
    vote_guidance=RoleActionGuidance(
        goal="从 candidates 中投给公开表现最可疑的目标。",
        constraints=("只能从 candidates 中选择",),
        priorities=("优先行为矛盾最多者", "避免完全随机"),
        style=("直接", "一致"),
    ),
    skill_guidance=RoleActionGuidance(
        goal="如果没有技能就遵守 legal_actions；若有特殊技能则按公开利益最大化。",
        constraints=("只能按 legal_actions 行动",),
        priorities=("不编造不存在的能力",),
        style=("朴素", "守规"),
    ),
)


IDIOT_PROFILE = RoleProfile(
    role="白痴",
    camp="villager",
    identity="立场偏好人、主要依赖公开信息发言的白痴",
    objective="通过稳定发言和公开投票帮助好人阵营识别狼人。",
    disclosure_policy="不冒充拥有夜间信息的神职，只基于公开信息表达判断。",
    cooperation_style="像可信好人一样持续输出一致立场，帮助场上建立共识。",
    behavior_tags=("public_reasoning", "steady_presence", "credibility_building"),
    speech_guidance=RoleActionGuidance(
        goal="基于公开发言和场上局势给出稳定、可信的好人判断。",
        constraints=("不能声称拥有查验或夜间信息",),
        priorities=("优先保持立场一致", "优先指出高嫌疑目标", "避免情绪化摇摆"),
        style=("自然", "坚定", "简洁"),
    ),
    vote_guidance=RoleActionGuidance(
        goal="从 candidates 中投给公开表现最可疑的目标。",
        constraints=("只能从 candidates 中选择",),
        priorities=("优先票出高嫌疑狼人", "避免无理由跟票"),
        style=("明确", "稳定"),
    ),
    skill_guidance=RoleActionGuidance(
        goal="当前没有主动技能，严格遵守 legal_actions。",
        constraints=("不能编造不存在的技能",),
        priorities=("无主动技能时保持 skip/不行动逻辑一致",),
        style=("守规", "朴素"),
    ),
)


ROLE_PROFILES: dict[str, RoleProfile] = {
    WEREWOLF_PROFILE.role: WEREWOLF_PROFILE,
    SEER_PROFILE.role: SEER_PROFILE,
    WITCH_PROFILE.role: WITCH_PROFILE,
    HUNTER_PROFILE.role: HUNTER_PROFILE,
    IDIOT_PROFILE.role: IDIOT_PROFILE,
    VILLAGER_PROFILE.role: VILLAGER_PROFILE,
}


def get_role_profile(role: str) -> RoleProfile:
    return ROLE_PROFILES.get(role, VILLAGER_PROFILE)
