"""
Centralized Authorization Service.
Implements Role-Based Access Control (RBAC) and context-aware permission evaluation.
All security decisions are centralized here rather than scattered throughout routes.
"""

import logging
from typing import Optional, Dict, Any

from app.core.exceptions import AuthorizationError
from app.core.logging import log_audit_event
from app.models import (
    EmployeeRecord,
    AuthorizationRole,
    AuthAction,
    AccessLevel,
    KnowledgeAsset,
    KnowledgeChunk,
)

logger = logging.getLogger("patchamomma.services.authz")


class AuthorizationService:
    """Centralized RBAC and policy decision point."""

    def authorize(
        self,
        actor: EmployeeRecord,
        action: AuthAction,
        resource: Optional[str] = None,
        target_employee: Optional[EmployeeRecord] = None,
        document: Optional[KnowledgeAsset] = None,
        raise_exception: bool = True,
    ) -> bool:
        """
        Evaluates whether an actor has permission to execute an action.
        Logs every decision to the immutable audit trail.
        If raise_exception is True, raises AuthorizationError (403) on denial.
        """
        is_allowed = self._evaluate_permission(actor, action, target_employee, document)
        resource_identifier = resource or (target_employee.employee_id if target_employee else "GLOBAL")

        if is_allowed:
            log_audit_event(
                "AUTHORIZATION_ALLOWED",
                actor.employee_id,
                action.value,
                "ALLOWED",
                resource_identifier,
                {"role": actor.authorization_role.value, "team": actor.team},
            )
            return True
        else:
            log_audit_event(
                "AUTHORIZATION_DENIED",
                actor.employee_id,
                action.value,
                "DENIED",
                resource_identifier,
                {"role": actor.authorization_role.value, "team": actor.team},
            )
            if raise_exception:
                raise AuthorizationError(
                    f"Forbidden: Employee '{actor.employee_id}' ({actor.authorization_role.value}) is not authorized for '{action.value}' on '{resource_identifier}'."
                )
            return False

    def _evaluate_permission(
        self,
        actor: EmployeeRecord,
        action: AuthAction,
        target_employee: Optional[EmployeeRecord],
        document: Optional[KnowledgeAsset],
    ) -> bool:
        role = actor.authorization_role

        # 1. Base Assistant Usage
        if action == AuthAction.USE_ASSISTANT:
            return True

        # 2. Self Operations
        if action in (
            AuthAction.VIEW_OWN_PROFILE,
            AuthAction.VIEW_OWN_ONBOARDING,
            AuthAction.COMPLETE_OWN_ONBOARDING_TASK,
            AuthAction.CHECK_TIMESHEET,
            AuthAction.CREATE_INCIDENT,
        ):
            if target_employee is None or target_employee.employee_id == actor.employee_id:
                return True
            # Checking someone else's profile/timesheet
            return self._can_access_target_employee(actor, target_employee)

        # 3. Team Progress & Subordinates
        if action in (AuthAction.VIEW_TEAM_MEMBERS, AuthAction.VIEW_TEAM_ONBOARDING):
            if role in (AuthorizationRole.MANAGER, AuthorizationRole.HR):
                return True
            return False

        # 4. View Other Employee Profile / Onboarding
        if action in (AuthAction.VIEW_EMPLOYEE_PROFILE, AuthAction.VIEW_EMPLOYEE_ONBOARDING):
            if target_employee is None or target_employee.employee_id == actor.employee_id:
                return True
            return self._can_access_target_employee(actor, target_employee)

        # 5. Update Employee Onboarding Status
        if action == AuthAction.UPDATE_EMPLOYEE_ONBOARDING:
            if role == AuthorizationRole.HR:
                return True
            if role == AuthorizationRole.MANAGER and target_employee and target_employee.manager_id == actor.employee_id:
                return True
            return False

        # 6. IT Administration & Permissions
        if action == AuthAction.MANAGE_PERMISSIONS:
            return role == AuthorizationRole.IT

        # 7. Document & Knowledge Access
        if action == AuthAction.VIEW_DOCUMENT:
            if not document:
                return True
            return self.can_access_document(actor, document)

        return False

    def _can_access_target_employee(self, actor: EmployeeRecord, target: EmployeeRecord) -> bool:
        """Determines if actor has hierarchical or administrative scope over target."""
        if actor.employee_id == target.employee_id:
            return True

        # HR and IT have cross-functional visibility
        if actor.authorization_role in (AuthorizationRole.HR, AuthorizationRole.IT):
            return True

        # Managers can view their direct reports or same-team subordinates
        if actor.authorization_role == AuthorizationRole.MANAGER:
            if target.manager_id == actor.employee_id or target.team.lower() == actor.team.lower():
                return True

        return False

    def can_access_document(self, actor: EmployeeRecord, document: KnowledgeAsset) -> bool:
        """Evaluates document-level Team ACL and AccessLevel clearance."""
        # Team clearance
        team_cleared = False
        if document.team == "ALL":
            team_cleared = True
        elif document.team.lower() == actor.team.lower():
            team_cleared = True
        elif actor.authorization_role == AuthorizationRole.HR and document.team == "HR":
            team_cleared = True
        elif actor.authorization_role == AuthorizationRole.IT and document.team == "IT":
            team_cleared = True

        if not team_cleared:
            return False

        # Access Level clearance
        if document.access_level == AccessLevel.EMPLOYEE:
            return True
        elif document.access_level == AccessLevel.MANAGER:
            return actor.authorization_role in (AuthorizationRole.MANAGER,)
        elif document.access_level == AccessLevel.HR:
            return actor.authorization_role in (AuthorizationRole.HR,)
        elif document.access_level == AccessLevel.IT:
            return actor.authorization_role in (AuthorizationRole.IT,)

        return False
