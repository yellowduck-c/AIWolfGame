from __future__ import annotations

from agent.roles.base_agent import BaseAgent
from agent.core.factory import build_agent
from agent.core.registry import AgentRegistry, agent_registry
from agent.roles.hunter_agent import HunterAgent
from agent.roles.idiot_agent import IdiotAgent
from agent.roles.seer_agent import SeerAgent
from agent.roles.villager_agent import VillagerAgent
from agent.roles.werewolf_agent import WerewolfAgent
from agent.roles.witch_agent import WitchAgent
from agent.state.memory import AgentDecisionHistory, AgentIdentityMemory, AgentMemory
from agent.state.schemas import AgentDecisionInput, SkillDecision, SkillResolution, SpeechDecision, StreamingSpeechDecision, VoteDecision
