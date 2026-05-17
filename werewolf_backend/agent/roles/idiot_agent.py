from __future__ import annotations

from agent.roles.base_agent import BaseAgent
from agent.roles.role_profiles import IDIOT_PROFILE, RoleProfile


class IdiotAgent(BaseAgent):
    def get_role_profile(self) -> RoleProfile:
        return IDIOT_PROFILE
