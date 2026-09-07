"""
Operations, Timesheet & Incident Sub-Agent.
Manages timesheet lookups, IT incident dispatching, and point-to-person lead escalations.
"""

import logging
from app.agents.tools.operations_tools import (
    check_my_timesheet_status,
    create_it_incident_ticket,
    resolve_team_blocker,
)

logger = logging.getLogger("patchamomma.agents.operations")


class OperationsAgent:
    name = "operations-action-agent"
    description = "Executes timesheet checks, IT incident ticket creation, and blocker escalation lookups."

    def execute(self, user_message: str) -> str:
        msg_lower = user_message.lower()

        # 1. Timesheet Intent
        if "timesheet" in msg_lower or "hours" in msg_lower or "submit time" in msg_lower:
            return check_my_timesheet_status()

        # 2. Incident Creation Intent
        if "incident" in msg_lower or "ticket" in msg_lower or "create issue" in msg_lower or "file bug" in msg_lower:
            category = "Cloud SQL / Database" if "sql" in msg_lower or "database" in msg_lower else (
                "Kubernetes / GKE" if "k8s" in msg_lower or "cluster" in msg_lower else "General IT / VPN"
            )
            return create_it_incident_ticket(category=category, summary=user_message, confirmed=True)

        # 3. Escalation / Contact / Blocker Intent
        domain = "Cloud SQL" if "sql" in msg_lower or "database" in msg_lower else (
            "Kubernetes" if "k8s" in msg_lower or "kubernetes" in msg_lower else (
                "IAM & Security" if "iam" in msg_lower or "security" in msg_lower else "Data Pipelines"
            )
        )
        return resolve_team_blocker(domain)


operations_agent = OperationsAgent()
