"""
Code Mentor Sub-Agent.
Analyzes codebases, explains system implementations, and enforces corporate logging standards.
"""

import logging
from app.agents.tools.code_tools import fetch_repository_context, apply_code_guardrails

logger = logging.getLogger("patchamomma.agents.code_mentor")


class CodeMentorAgent:
    name = "code-mentor-agent"
    description = "Provides code explanations, repository search, and corporate structured logging guardrail enforcement."

    def execute(self, user_message: str) -> str:
        msg_lower = user_message.lower()

        # Identify target file or query
        if "database" in msg_lower or "sql" in msg_lower or "connect" in msg_lower:
            return fetch_repository_context(
                repo_name="patchamomma-core",
                query="database connection",
                file_path="backend/database/connection.py",
            )
        elif "jwt" in msg_lower or "token" in msg_lower or "auth" in msg_lower:
            return fetch_repository_context(
                repo_name="patchamomma-core",
                query="jwt validator",
                file_path="services/auth/jwt_validator.py",
            )
        else:
            return fetch_repository_context(
                repo_name="patchamomma-core",
                query=user_message,
            )


code_mentor_agent = CodeMentorAgent()
