from __future__ import annotations

from agent.roles.base_agent import BaseAgent
from agent.roles.role_profiles import RoleProfile, VILLAGER_PROFILE


class VillagerAgent(BaseAgent):
    def get_role_profile(self) -> RoleProfile:
        return VILLAGER_PROFILE
