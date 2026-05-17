from __future__ import annotations

from agent.roles.base_agent import BaseAgent
from agent.roles.role_profiles import RoleProfile, SEER_PROFILE


class SeerAgent(BaseAgent):
    def get_role_profile(self) -> RoleProfile:
        return SEER_PROFILE
