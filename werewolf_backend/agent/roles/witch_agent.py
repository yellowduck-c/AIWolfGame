from __future__ import annotations

from agent.roles.base_agent import BaseAgent
from agent.roles.role_profiles import RoleProfile, WITCH_PROFILE


class WitchAgent(BaseAgent):
    def get_role_profile(self) -> RoleProfile:
        return WITCH_PROFILE
