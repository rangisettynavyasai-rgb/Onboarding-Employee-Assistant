"""
Onboarding Service.
Orchestrates employee onboarding checklists, milestone tracking, and manager team progress rollups.
"""

import logging
from typing import List, Optional

from app.core.exceptions import NotFoundError, AuthorizationError
from app.core.logging import log_audit_event
from app.models import (
    EmployeeRecord,
    OnboardingChecklist,
    OnboardingTask,
    TeamOnboardingSummary,
    AuthAction,
)
from app.repositories.base import IOnboardingRepository, IEmployeeRepository
from app.services.authorization_service import AuthorizationService

logger = logging.getLogger("patchamomma.services.onboarding")


class OnboardingService:
    """Manages employee onboarding lifecycle and manager progress dashboards."""

    def __init__(
        self,
        onboarding_repo: IOnboardingRepository,
        employee_repo: IEmployeeRepository,
        authz_service: AuthorizationService,
    ):
        self.onboarding_repo = onboarding_repo
        self.employee_repo = employee_repo
        self.authz_service = authz_service

    def get_employee_checklist(self, actor: EmployeeRecord, target_employee_id: str) -> OnboardingChecklist:
        """
        Retrieves onboarding checklist for a target employee with authorization check.
        """
        target = self.employee_repo.get_by_id(target_employee_id)
        if not target:
            raise NotFoundError(f"Employee '{target_employee_id}' not found.")

        # Authorize: Is actor allowed to view target's onboarding?
        self.authz_service.authorize(
            actor=actor,
            action=AuthAction.VIEW_OWN_ONBOARDING if actor.employee_id == target.employee_id else AuthAction.VIEW_EMPLOYEE_ONBOARDING,
            target_employee=target,
            resource=f"ONBOARDING_{target.employee_id}",
        )

        checklist = self.onboarding_repo.get_checklist(target.employee_id)
        if not checklist:
            raise NotFoundError(f"No onboarding checklist found for '{target.employee_id}'.")
        return checklist

    def complete_onboarding_task(self, actor: EmployeeRecord, task_id: str, target_employee_id: Optional[str] = None) -> OnboardingChecklist:
        """
        Marks an onboarding task as completed for an employee.
        """
        target_id = target_employee_id or actor.employee_id
        target = self.employee_repo.get_by_id(target_id)
        if not target:
            raise NotFoundError(f"Employee '{target_id}' not found.")

        # Authorize action
        action = AuthAction.COMPLETE_OWN_ONBOARDING_TASK if actor.employee_id == target.employee_id else AuthAction.UPDATE_EMPLOYEE_ONBOARDING
        self.authz_service.authorize(
            actor=actor,
            action=action,
            target_employee=target,
            resource=f"TASK_{task_id}",
        )

        success = self.onboarding_repo.complete_task(target_id, task_id)
        if not success:
            raise NotFoundError(f"Task '{task_id}' not found on checklist for employee '{target_id}'.")

        log_audit_event("TASK_COMPLETED", actor.employee_id, "COMPLETE_TASK", "EXECUTED", task_id, {"target_id": target_id})
        return self.get_employee_checklist(actor, target_id)

    def get_team_onboarding_progress(self, actor: EmployeeRecord, team_name: Optional[str] = None) -> TeamOnboardingSummary:
        """
        Retrieves onboarding status rollup for a manager's team.
        Requires MANAGER or HR role.
        """
        self.authz_service.authorize(
            actor=actor,
            action=AuthAction.VIEW_TEAM_ONBOARDING,
            resource=f"TEAM_{team_name or actor.team}",
        )

        target_team = team_name or actor.team
        members_progress = self.onboarding_repo.get_team_progress(actor.employee_id, target_team)

        fully_completed = sum(1 for m in members_progress if m.completed_count == m.total_count)

        return TeamOnboardingSummary(
            team_name=target_team,
            manager_id=actor.employee_id,
            manager_name=actor.name,
            total_team_members=len(members_progress),
            fully_onboarded_count=fully_completed,
            members=members_progress,
        )
