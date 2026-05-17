from __future__ import annotations

from agent.roles.base_agent import BaseAgent
from agent.roles.role_profiles import RoleProfile, HUNTER_PROFILE


class HunterAgent(BaseAgent):
    def get_role_profile(self) -> RoleProfile:
        return HUNTER_PROFILE
