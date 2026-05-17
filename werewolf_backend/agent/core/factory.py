from __future__ import annotations

from agent.roles.base_agent import BaseAgent
from agent.roles.hunter_agent import HunterAgent
from agent.roles.idiot_agent import IdiotAgent
from agent.roles.seer_agent import SeerAgent
from agent.roles.villager_agent import VillagerAgent
from agent.roles.werewolf_agent import WerewolfAgent
from agent.roles.witch_agent import WitchAgent


def build_agent(player_id: int, role: str, camp: str) -> BaseAgent:
    if role == "狼人":
        return WerewolfAgent(player_id=player_id, role=role, camp=camp)
    if role == "预言家":
        return SeerAgent(player_id=player_id, role=role, camp=camp)
    if role == "女巫":
        return WitchAgent(player_id=player_id, role=role, camp=camp)
    if role == "猎人":
        return HunterAgent(player_id=player_id, role=role, camp=camp)
    if role == "白痴":
        return IdiotAgent(player_id=player_id, role=role, camp=camp)
    return VillagerAgent(player_id=player_id, role=role, camp=camp)
