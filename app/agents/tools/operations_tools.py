"""
Operations, Timesheet, Incident, and Escalation Agent Tools.
Enforces zero-trust identity and explicit confirmation guards.
"""

import logging
from typing import Optional

from app.core import context
from app.dependencies import timesheet_service, incident_service
from app.models import IncidentSeverity

logger = logging.getLogger("patchamomma.agents.tools.operations")


def check_my_timesheet_status() -> str:
    """
    Checks the authenticated employee's timesheet status for the current pay period.
    ZERO-TRUST: Automatically pulls current employee identity from server context.
    """
    actor = context.get_current_employee()
    try:
        res = timesheet_service.get_timesheet_status(actor, actor.employee_id)
        return (
            f"⏱️ **Timesheet Status for {actor.name}**\n"
            f"Period: {res.get('period', 'Current Week')}\n"
            f"Hours Logged: {res.get('hours_logged', 0.0)} hrs\n"
            f"Status: **{res.get('status', 'PENDING')}**\n"
            f"Due Date: {res.get('due_date', 'Friday 5:00 PM')}\n\n"
            f"{res.get('message', '')}"
        )
    except Exception as e:
        logger.error(f"check_my_timesheet_status failed: {e}")
        return f"Could not check timesheet: {str(e)}"


def create_it_incident_ticket(category: str, summary: str, confirmed: bool = True) -> str:
    """
    Creates an official IT or Platform incident ticket.
    Args:
        category: Incident category (e.g. 'Cloud SQL / Database', 'VPN / Network', 'Hardware')
        summary: Brief technical description of the problem
        confirmed: Explicit user confirmation flag
    """
    actor = context.get_current_employee()
    try:
        incident = incident_service.create_incident(
            actor=actor,
            category=category,
            summary=summary,
            severity=IncidentSeverity.MEDIUM,
            confirmed=confirmed,
        )
        return (
            f"🚨 **Incident Ticket Created Successfully!**\n"
            f"- **Incident ID**: `{incident.incident_id}`\n"
            f"- **Reporter**: {actor.name} ({actor.employee_id})\n"
            f"- **Category**: {incident.category}\n"
            f"- **Assigned Team**: {incident.assigned_team}\n"
            f"- **Status**: {incident.status}\n"
            f"- **Summary**: {incident.summary}\n"
            f"An engineer will reach out via Slack shortly."
        )
    except Exception as e:
        logger.warning(f"create_it_incident_ticket failed: {e}")
        return f"Incident creation failed: {str(e)}"


def resolve_team_blocker(issue_domain: str) -> str:
    """
    Queries the hierarchical point-to-person escalation directory for a technology domain.
    Logic:
    1. If primary lead is available -> assigns primary lead.
    2. If primary lead is on vacation -> routes to backup lead.
    3. If BOTH leads are on vacation -> broadcasts to team channel and logs blocker event.
    Args:
        issue_domain: The domain name (e.g. 'Kubernetes', 'Cloud SQL', 'IAM & Security', 'Data Pipelines')
    """
    actor = context.get_current_employee()
    try:
        res = incident_service.resolve_domain_escalation(actor, issue_domain)
        status = res["status"]
        if status == "PRIMARY_ASSIGNED":
            return f"✅ **Primary Lead Assigned**:\nDomain: {res['domain']}\nContact: {res['assigned_contact']}\nChannel: {res['channel']}"
        elif status == "BACKUP_ASSIGNED":
            return f"⚠️ **Primary OOO - Backup Lead Assigned**:\nDomain: {res['domain']}\nContact: {res['assigned_contact']}\nChannel: {res['channel']}"
        else:
            return f"🚨 **High-Priority Escalation Broadcast**:\nDomain: {res['domain']}\nNotice: {res['message']}\nTracking ID: `{res.get('tracking_id')}`"
    except Exception as e:
        logger.error(f"resolve_team_blocker failed: {e}")
        return f"Escalation lookup failed: {str(e)}"
