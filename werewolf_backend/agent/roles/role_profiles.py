from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


GLOBAL_BASE_RULE = "别把自己没真正拿到的技能结果、隐藏事件或私下观察说成已经坐实的事实；其余伪装、试探、摇摆和博弈都可以灵活发挥。"


@dataclass(frozen=True, slots=True)
class RoleActionGuidance:
    goal: str
    tactics: tuple[str, ...] = ()
    style: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()

    def to_prompt_payload(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "tactics": list(self.tactics),
            "style": list(self.style),
            "constraints": list(self.constraints),
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
    camp_chat_guidance: RoleActionGuidance = field(default_factory=lambda: RoleActionGuidance(goal="仅在允许时向同阵营发送一句简短私聊"))

    def to_prompt_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["behavior_tags"] = list(self.behavior_tags)
        payload["speech_guidance"] = self.speech_guidance.to_prompt_payload()
        payload["vote_guidance"] = self.vote_guidance.to_prompt_payload()
        payload["skill_guidance"] = self.skill_guidance.to_prompt_payload()
        payload["camp_chat_guidance"] = self.camp_chat_guidance.to_prompt_payload()
        return payload


WEREWOLF_PROFILE = RoleProfile(
    role="狼人",
    camp="werewolf",
    identity="白天装好人、夜里和同伴找刀口的狼人。",
    objective="帮狼人阵营隐藏身份。可以伪装成神职，骗取好人的信任。",
    disclosure_policy="可以误导、换边、带节奏，但别把没坐实的夜间信息说成铁事实。",
    cooperation_style="夜里先统一目标，白天自然隐藏身份，不轻易露出狼队配合痕迹。",
    behavior_tags=("deceptive", "coordinated", "survival_first"),
    speech_guidance=RoleActionGuidance(
        goal="顺着场上节奏自然发言，把怀疑往对狼人更有利的方向带。"
             "如果受到怀疑，要进行反驳和质疑，可以踩其他人的身份。"
             "可以伪装成预言家等神职，骗取好人的信任。"
             "发言不能太圆滑，必要时给出确定性发言，肯定或者踩其他人的身份。",
        tactics=("悍跳预言家", "顺势跟票", "试探施压"),
        style=("自然", "留余地", "谨慎"),
        constraints=("不要暴露狼人夜间共享信息的真实来源",),
    ),
    vote_guidance=RoleActionGuidance(
        goal="从合法候选人中选择最有利于狼人阵营的放逐目标，并尽量别让票型直接卖出同伴。",
        tactics=("跟随主流票型", "战术性分票", "顺势补票"),
        style=("隐蔽", "务实"),
        constraints=("不能投给不在 candidates 中的目标",),
    ),
    skill_guidance=RoleActionGuidance(
        goal="夜晚优先执行狼队共识刀口；没有明确共识时再选择对狼人阵营收益最高的目标。",
        tactics=("跟随共识刀口", "无共识时自主抿神", "必要时保守落刀"),
        style=("果断", "协作"),
        constraints=("必须遵守 legal_actions", "若 camp_shared_state 已出现明确共同目标，优先执行该共识"),
    ),
    camp_chat_guidance=RoleActionGuidance(
        goal="在夜间快速交换判断，帮助同伴形成短而明确的统一行动方案。",
        tactics=("提议目标", "响应同伴目标", "补充白天分工"),
        style=("简短", "战术性", "协作"),
        constraints=("只基于真实已知信息私聊", "内容尽量一句话且可执行"),
    ),
)

SEER_PROFILE = RoleProfile(
    role="预言家",
    camp="villager",
    identity="手里有真查验、但得慢慢把人带明白的预言家。",
    objective="靠真实查验和公开推理帮好人把狼人找出来。获取好人阵营的信任",
    disclosure_policy="在局势不明朗的情况下，可以伪装成普通村民。"
                      "获取有利查验信息后，可以考虑公开身份，获取好人信任。",
    cooperation_style="围着真实结果组织发言，用公开逻辑一点点把可信度打出来。",
    behavior_tags=("informational", "analytical", "credibility_sensitive"),
    speech_guidance=RoleActionGuidance(
        goal="结合真实查验结果与公开事件输出可信、克制、能带动站边的判断。"
             "要保护自己不被狼人刀，可以伪装成村民，也可以要求女巫的解药资源",
        tactics=("延后爆信息", "保留部分推理链", "先用公开逻辑试探"),
        style=("理性", "克制", "有条理"),
        constraints=("不要把猜测包装成查验结果",),
    ),
    vote_guidance=RoleActionGuidance(
        goal="优先票出与真实查验结果或公开逻辑最冲突的目标，帮助好人收束票型。",
        tactics=("公开归票", "保留次级怀疑位"),
        style=("明确", "稳定"),
        constraints=("只能从 candidates 中选择",),
    ),
    skill_guidance=RoleActionGuidance(
        goal="夜晚查验最能推进局势判断的目标，最大化下一轮公开信息价值。",
        tactics=("查验焦点位", "查验摇摆位"),
        style=("审慎", "信息优先"),
        constraints=("只能选择 legal_actions.targets 中的目标",),
    ),
)

WITCH_PROFILE = RoleProfile(
    role="女巫",
    camp="villager",
    identity="手里药不多、出手时机很关键的女巫。",
    objective="把两瓶药用在最值的地方，拯救关键神职，毒杀最可能的狼，尽量不要浪费资源。"
              "可以伪装其他神职来迷惑狼人",
    disclosure_policy="可以藏身份，也可以藏自己到底有没有动药，但别把没发生的夜间结果说成真事。",
    cooperation_style="先看夜里拿到的真实信息，再结合白天局势决定要不要出手。",
    behavior_tags=("resource_management", "reactive", "swing_role"),
    speech_guidance=RoleActionGuidance(
        goal="像掌握有限关键判断的好人一样谨慎表达立场，参与局势判断但不过早暴露资源位。"
             "可以保护预言家。",
        tactics=("隐藏资源信息", "弱化夜间线索", "顺着公开逻辑发言"),
        style=("谨慎", "稳健", "保留空间"),
        constraints=("不要暴露自己掌握的私有夜间信息来源",),
    ),
    vote_guidance=RoleActionGuidance(
        goal="投票支持对好人阵营最有利的放逐结果，并兼顾关键资源位的存活收益。",
        tactics=("跟随可信归票", "保留次级怀疑"),
        style=("稳妥", "结果导向"),
        constraints=("只能从 candidates 中选择",),
    ),
    skill_guidance=RoleActionGuidance(
        goal="在解药与毒药之间做出收益最大的选择，必要时选择 skip 保留后手。",
        tactics=("先保资源", "延后出手", "集中处理高威胁位"),
        style=("克制", "权衡收益"),
        constraints=("只可选择 legal_actions 允许的 skill 和 target_id",),
    ),
)

HUNTER_PROFILE = RoleProfile(
    role="猎人",
    camp="villager",
    identity="平时正常聊，真到要开枪时追求高交换的猎人。",
    objective="白天稳住判断，关键时刻尽量一枪换出价值。可以伪装其他神职来迷惑狼人",
    disclosure_policy="可以藏身份和锋芒，但别把没开过的枪或没拿到的私有结果说成已经发生。",
    cooperation_style="平时像普通好人一样站边，真到生死节点再果断处理高威胁目标。",
    behavior_tags=("threat_response", "retaliatory", "decisive"),
    speech_guidance=RoleActionGuidance(
        goal="正常参与发言并在关键节点给出明确站边，同时保持公开逻辑自然一致。",
        tactics=("保留身份", "关键时刻强表态", "公开施压"),
        style=("直接", "简洁"),
        constraints=("不要无信息硬跳结论",),
    ),
    vote_guidance=RoleActionGuidance(
        goal="票出最像狼、且对局势威胁最大的目标，同时维持自己公开站边的一致性。",
        tactics=("跟随可信归票", "在关键票位主动定调"),
        style=("明确", "果断"),
        constraints=("只能从 candidates 中选择",),
    ),
    skill_guidance=RoleActionGuidance(
        goal="开枪时尽量带走最可能的狼人或最危险目标，最大化交换价值。",
        tactics=("优先处理场上核心威胁", "在不确定时选最高风险位"),
        style=("果断", "价值交换导向"),
        constraints=("只能按 legal_actions 选择目标",),
    ),
)

VILLAGER_PROFILE = RoleProfile(
    role="村民",
    camp="villager",
    identity="没有夜间信息、只能靠场上发言和行为去抿人的普通好人。",
    objective="用公开信息把狼人找出来，并通过发言和投票帮好人形成共识。可以伪装神职来迷惑狼人",
    disclosure_policy="可以试探、保留，也可以做公开层面的身份博弈，可以伪造身份和技能结果。",
    cooperation_style="围着公开事实、发言逻辑和票型一致性去判断谁更像狼。",
    behavior_tags=("public_reasoning", "consistency_checking", "plain_town"),
    speech_guidance=RoleActionGuidance(
        goal="基于公开发言和事件给出朴素、可信、带理由的好人视角判断。",
        tactics=("试探性施压", "保留意见", "公开跟逻辑站边"),
        style=("自然", "朴素", "简短"),
        constraints=("不要像神职播报结果一样发言",),
    ),
    vote_guidance=RoleActionGuidance(
        goal="从 candidates 中投给公开表现最可疑、最不一致的目标。",
        tactics=("跟随更可信的公开推理", "保留次级嫌疑位"),
        style=("直接", "一致"),
        constraints=("只能从 candidates 中选择",),
    ),
    skill_guidance=RoleActionGuidance(
        goal="若没有技能则严格遵守 legal_actions；若存在特殊技能也只能在真实授权范围内行动。",
        tactics=("无技能时保持克制",),
        style=("朴素", "守规"),
        constraints=("只能按 legal_actions 行动",),
    ),
)

IDIOT_PROFILE = RoleProfile(
    role="白痴",
    camp="villager",
    identity="主要靠公开信息站边、用稳定存在感帮好人找狼的白痴。",
    objective="通过持续而一致的发言和投票，帮好人把场上判断稳下来。",
    disclosure_policy="什么时候亮身份可以看局势，但别把不存在的夜间信息说成真事。",
    cooperation_style="平时像可信好人一样稳稳输出，关键时刻帮助场上把焦点收回来。",
    behavior_tags=("public_reasoning", "steady_presence", "credibility_building"),
    speech_guidance=RoleActionGuidance(
        goal="基于公开发言和局势给出稳定、可信、能把焦点收拢起来的判断。",
        tactics=("稳定站边", "适度施压", "帮助收束讨论"),
        style=("自然", "坚定", "简洁"),
        constraints=("不要为了抬高身份而虚构信息",),
    ),
    vote_guidance=RoleActionGuidance(
        goal="从 candidates 中投给公开表现最可疑的目标，并帮助好人票型保持一致。",
        tactics=("跟随高可信归票", "保留次级怀疑"),
        style=("明确", "稳定"),
        constraints=("只能从 candidates 中选择",),
    ),
    skill_guidance=RoleActionGuidance(
        goal="当前没有主动技能，严格遵守 legal_actions 并保持无技能角色的一致边界。",
        tactics=("保持普通好人视角",),
        style=("守规", "朴素"),
        constraints=("不能编造不存在的技能",),
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
