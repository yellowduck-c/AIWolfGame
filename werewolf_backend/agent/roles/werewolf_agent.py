from __future__ import annotations

from agent.roles.base_agent import BaseAgent
from agent.roles.role_profiles import RoleProfile, WEREWOLF_PROFILE


class WerewolfAgent(BaseAgent):
    def get_role_profile(self) -> RoleProfile:
        return WEREWOLF_PROFILE
