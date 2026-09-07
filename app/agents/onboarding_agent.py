"""
Onboarding Specialist Sub-Agent.
Specializes in welcoming new joiners, guiding checklist tasks, and reporting team onboarding status.
"""

import logging
from typing import Dict, Any, Optional

from app.core import context
from app.agents.tools.onboarding_tools import (
    get_my_onboarding_status,
    complete_my_onboarding_task,
    get_team_onboarding_progress,
)

logger = logging.getLogger("patchamomma.agents.onboarding")


class OnboardingAgent:
    name = "onboarding-specialist-agent"
    description = "Handles employee onboarding checklists, Day-1 orientation, and manager team progress tracking."

    def execute(self, user_message: str) -> str:
        msg_lower = user_message.lower()
        actor = context.get_current_employee()

        # Manager team inquiry
        if "team" in msg_lower and ("progress" in msg_lower or "onboard" in msg_lower or "status" in msg_lower or "members" in msg_lower or "how is" in msg_lower):
            return get_team_onboarding_progress()

        # Complete task inquiry
        if "complete" in msg_lower or "done" in msg_lower or "finish" in msg_lower:
            # Look for task ID pattern or complete first pending
            import re
            match = re.search(r"(task-[a-z0-9\-]+)", msg_lower)
            if match:
                return complete_my_onboarding_task(match.group(1).upper())
            else:
                return complete_my_onboarding_task("TASK-001-ENV")

        # Default: Return personal onboarding checklist and status
        return get_my_onboarding_status()


onboarding_agent = OnboardingAgent()
