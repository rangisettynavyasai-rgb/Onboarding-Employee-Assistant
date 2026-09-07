"""
Incident Management & Escalation Service.
Manages IT/Platform incident ticket creation and hierarchical team lead escalation routing.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from app.core.exceptions import ValidationError
from app.core.logging import log_audit_event
from app.models import (
    EmployeeRecord,
    IncidentRecord,
    IncidentSeverity,
    AuthAction,
    TeamEscalationContact,
)
from app.repositories.base import IOperationsRepository
from app.services.authorization_service import AuthorizationService

logger = logging.getLogger("patchamomma.services.incident")


class IncidentService:
    """Manages IT/Engineering incident creation and point-to-person escalation routing."""

    def __init__(self, operations_repo: IOperationsRepository, authz_service: AuthorizationService):
        self.operations_repo = operations_repo
        self.authz_service = authz_service

    def create_incident(
        self,
        actor: EmployeeRecord,
        category: str,
        summary: str,
        severity: IncidentSeverity = IncidentSeverity.MEDIUM,
        confirmed: bool = True,
    ) -> IncidentRecord:
        """
        Creates a new IT/Platform incident with validation and user confirmation guard.
        """
        if not confirmed:
            raise ValidationError("Incident creation requires explicit user confirmation.")

        if not summary or len(summary.strip()) < 5:
            raise ValidationError("Incident summary must be at least 5 characters long.")

        self.authz_service.authorize(
            actor=actor,
            action=AuthAction.CREATE_INCIDENT,
            resource=f"INCIDENT_{category}",
        )

        incident_id = f"INC-2026-{uuid.uuid4().hex[:6].upper()}"
        assigned_team = "Platform" if "sql" in category.lower() or "database" in category.lower() or "k8s" in category.lower() else "IT-Support"

        incident = IncidentRecord(
            incident_id=incident_id,
            created_by=actor.employee_id,
            category=category,
            summary=summary,
            severity=severity,
            status="OPEN",
            assigned_team=assigned_team,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        saved = self.operations_repo.create_incident(incident)
        log_audit_event("INCIDENT_CREATED", actor.employee_id, "CREATE_INCIDENT", "EXECUTED", incident_id, {"severity": severity.value, "category": category})

        # Log telemetry stream event
        self.operations_repo.stream_telemetry({
            "log_id": str(uuid.uuid4()),
            "user_id": actor.employee_id,
            "user_role": actor.job_role,
            "assigned_team": actor.team,
            "query_timestamp": datetime.now(timezone.utc).isoformat(),
            "user_query_intent": f"CREATE_INCIDENT_{category.upper()}",
            "resolution_status": f"INCIDENT_DISPATCHED_{incident_id}",
            "friction_duration_minutes": 10,
            "blocker_severity": severity.value,
        })

        return saved

    def resolve_domain_escalation(self, actor: EmployeeRecord, domain: str) -> Dict[str, Any]:
        """
        Evaluates the point-to-person hierarchical escalation matrix for a system domain.
        """
        contact = self.operations_repo.get_escalation_contact(domain)
        if not contact:
            return {
                "domain": domain,
                "status": "FALLBACK_GENERAL",
                "assigned_contact": "IT Service Desk",
                "channel": "#general-it-helpdesk",
                "message": f"No specific point-of-contact registered for '{domain}'. Routed to #general-it-helpdesk.",
            }

        # Case 1: Primary Lead Available
        if not contact.primary_on_vacation:
            return {
                "domain": domain,
                "status": "PRIMARY_ASSIGNED",
                "assigned_contact": f"{contact.primary_lead_name} ({contact.primary_email})",
                "channel": contact.general_channel,
                "message": f"Assigned to Primary Lead: {contact.primary_lead_name} ({contact.primary_email}). Available on Slack.",
            }

        # Case 2: Primary Lead OOO -> Backup Available
        if contact.primary_on_vacation and not contact.backup_on_vacation:
            return {
                "domain": domain,
                "status": "BACKUP_ASSIGNED",
                "assigned_contact": f"{contact.backup_lead_name} ({contact.backup_email})",
                "channel": contact.general_channel,
                "message": f"Primary Lead ({contact.primary_lead_name}) is Out of Office. Re-routed to Backup Lead: {contact.backup_lead_name} ({contact.backup_email}).",
            }

        # Case 3: BOTH Leads OOO -> Broadcast Channel & High Priority Friction Log
        telemetry_id = str(uuid.uuid4())
        self.operations_repo.stream_telemetry({
            "log_id": telemetry_id,
            "user_id": actor.employee_id,
            "user_role": actor.job_role,
            "assigned_team": actor.team,
            "query_timestamp": datetime.now(timezone.utc).isoformat(),
            "user_query_intent": f"ESCALATION_BLOCKER_{domain.upper()}",
            "resolution_status": "ROADBLOCK_BOTH_LEADS_OOO",
            "friction_duration_minutes": 30,
            "blocker_severity": "HIGH",
        })

        return {
            "domain": domain,
            "status": "BOTH_OOO_BROADCAST_TRIGGERED",
            "assigned_contact": f"Broadcast Channel ({contact.general_channel})",
            "channel": contact.general_channel,
            "tracking_id": telemetry_id,
            "message": f"High Priority Alert: Both Primary ({contact.primary_lead_name}) and Backup ({contact.backup_lead_name}) leads are Out of Office. Ticket broadcasted to {contact.general_channel}.",
        }
