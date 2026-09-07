"""
Employee Service.
Maps external Google Identity Principal to trusted internal EmployeeRecord.
"""

import logging
from typing import List, Optional

from app.core.exceptions import AuthenticationError, NotFoundError
from app.core.logging import log_audit_event
from app.models import AuthenticatedPrincipal, EmployeeRecord
from app.repositories.base import IEmployeeRepository

logger = logging.getLogger("patchamomma.services.employee")


class EmployeeService:
    """Manages identity resolution and employee directory queries."""

    def __init__(self, employee_repo: IEmployeeRepository):
        self.employee_repo = employee_repo

    def resolve_principal_to_employee(self, principal: AuthenticatedPrincipal) -> EmployeeRecord:
        """
        Maps a verified Google Identity (subject or email) to an internal EmployeeRecord.
        Raises AuthenticationError (401) if identity is not registered.
        """
        # 1. Primary lookup: Google Subject ID (sub)
        employee = self.employee_repo.get_by_google_subject(principal.subject)

        # 2. Fallback lookup: Verified corporate email address
        if not employee and principal.email:
            for emp in self.employee_repo.list_all():
                if emp.email.lower() == principal.email.lower():
                    employee = emp
                    break

        if not employee:
            log_audit_event(
                "IDENTITY_MAPPING_FAILED",
                principal.subject,
                "RESOLVE_EMPLOYEE",
                "DENIED",
                "EMPLOYEE_DIRECTORY",
                {"email": principal.email},
            )
            raise AuthenticationError(
                f"Google identity '{principal.email}' (sub: {principal.subject}) is not registered in the employee directory."
            )

        log_audit_event(
            "IDENTITY_MAPPED",
            employee.employee_id,
            "RESOLVE_EMPLOYEE",
            "ALLOWED",
            "EMPLOYEE_DIRECTORY",
            {"role": employee.authorization_role.value, "team": employee.team},
        )
        return employee

    def get_employee_by_id(self, employee_id: str) -> EmployeeRecord:
        """Looks up an employee by internal ID."""
        emp = self.employee_repo.get_by_id(employee_id)
        if not emp:
            raise NotFoundError(f"Employee '{employee_id}' not found.")
        return emp

    def get_team_members(self, team: str) -> List[EmployeeRecord]:
        """Returns all employees in a specific team."""
        return self.employee_repo.get_by_team(team)

    def get_direct_reports(self, manager_id: str) -> List[EmployeeRecord]:
        """Returns direct reports assigned to a manager."""
        return self.employee_repo.get_by_manager_id(manager_id)
