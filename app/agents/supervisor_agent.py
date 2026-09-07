"""
Master Workforce Supervisor & Multi-Agent Orchestrator (Phase E: Pay-Per-Token Model Enforcement).
Classifies user intent, delegates execution to domain sub-agents, manages multi-turn session state,
and executes serverless direct Gemini API invocations without persistent compute cluster overhead.
"""

import logging
from typing import Dict, Any, Tuple, Optional

from app.config import settings
from app.core import context
from app.models import EmployeeRecord
from app.services.session_service import UserSession
from app.agents.onboarding_agent import onboarding_agent
from app.agents.knowledge_agent import knowledge_agent
from app.agents.code_mentor_agent import code_mentor_agent
from app.agents.operations_agent import operations_agent

logger = logging.getLogger("patchamomma.agents.supervisor")


class SupervisorAgent:
    """Master Orchestrator coordinating specialized domain sub-agents with pay-per-token routing."""

    def __init__(self):
        self.sub_agents = {
            onboarding_agent.name: onboarding_agent,
            knowledge_agent.name: knowledge_agent,
            code_mentor_agent.name: code_mentor_agent,
            operations_agent.name: operations_agent,
        }
        self._gemini_client = None

    def dispatch(self, user_message: str, session: UserSession, employee: EmployeeRecord) -> Tuple[str, str]:
        """
        Dispatches the user's message to the appropriate specialized agent.
        Returns (response_text, agent_name).
        """
        msg_lower = user_message.lower()
        selected_agent_name = self._classify_intent(msg_lower, employee)
        agent = self.sub_agents[selected_agent_name]

        logger.info(f"Supervisor dispatching message to '{selected_agent_name}' for employee '{employee.employee_id}'")

        # Record user message in session history
        session.append_message("user", user_message)

        # Execute specialized sub-agent
        response_text = agent.execute(user_message)

        # Record assistant response in session history
        session.append_message("assistant", response_text)

        return response_text, selected_agent_name

    def generate_direct_response(self, user_prompt: str, context_data: str) -> str:
        """
        Direct serverless pay-per-token Gemini API call without dedicated endpoint idle compute fees.
        """
        api_key = settings.GEMINI_API_KEY or settings.get_secret("gemini-api-key")
        if api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(settings.GEMINI_MODEL)
                full_prompt = f"{context_data}\n\nUser Question: {user_prompt}\n\nPlease provide a concise, helpful response adhering strictly to the above security perimeter."
                resp = model.generate_content(
                    full_prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=settings.TEMPERATURE,
                        max_output_tokens=settings.MAX_OUTPUT_TOKENS,
                    ),
                )
                if resp and resp.text:
                    return resp.text.strip()
            except Exception as e:
                logger.warning(f"Direct Gemini API call failed: {e}. Falling back to domain sub-agents.")

        # Fallback to deterministic intent execution
        emp = context.get_current_employee()
        selected_agent_name = self._classify_intent(user_prompt.lower(), emp)
        return self.sub_agents[selected_agent_name].execute(user_prompt)

    def _classify_intent(self, msg_lower: str, employee: EmployeeRecord) -> str:
        """Determines the most appropriate specialized sub-agent based on query semantics."""
        # 1. Operational Actions: Timesheet, Incident, Blocker, Vacation, On-call
        if any(kw in msg_lower for kw in ("timesheet", "incident", "ticket", "blocker", "escalat", "vacation", "lead", "on call", "who to contact")):
            return operations_agent.name

        # 2. Knowledge & Runbooks: Runbook, manual, doc, guide, policy, compensation, 1:1, architecture blueprint, video, conduct
        if any(kw in msg_lower for kw in ("code of conduct", "policy", "guideline", "manual", "runbook", "compensation", "playbook", "video", "timestamp", "pdf", "search knowledge", "working hours")):
            return knowledge_agent.name

        # 3. Engineering Code & Standards: Code, repo, database connection, refactor, function, syntax
        if any(kw in msg_lower for kw in ("codebase", "repository", "repo", "connection.py", "jwt_validator", "refactor", "print(", "function", "logger", "standards", "code")):
            return code_mentor_agent.name

        # 4. Onboarding, Tasks & Orientation: Onboard, task, checklist, day 1, welcome, hello, hi, progress, buddy
        if any(kw in msg_lower for kw in ("onboard", "task", "checklist", "day 1", "welcome", "hello", "hi", "hey", "progress", "buddy", "complete")):
            return onboarding_agent.name

        # Fallback to Onboarding if Day-1, else Knowledge Agent
        if employee.is_day_one:
            return onboarding_agent.name

        return knowledge_agent.name


supervisor_agent = SupervisorAgent()
