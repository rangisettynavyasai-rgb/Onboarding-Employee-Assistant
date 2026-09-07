"""
Timesheet Integration Service.
Provides employee timesheet lookups and overdue reminder calculations.
"""

import logging
from typing import List, Optional, Dict, Any

from app.core.exceptions import NotFoundError, AuthorizationError
from app.core.logging import log_audit_event
from app.models import EmployeeRecord, TimesheetRecord, TimesheetStatus, AuthAction
from app.repositories.base import IOperationsRepository, IEmployeeRepository
from app.services.authorization_service import AuthorizationService

logger = logging.getLogger("patchamomma.services.timesheet")


class TimesheetService:
    """Manages enterprise timesheet queries and compliance reminders."""

    def __init__(
        self,
        operations_repo: IOperationsRepository,
        employee_repo: IEmployeeRepository,
        authz_service: AuthorizationService,
    ):
        self.operations_repo = operations_repo
        self.employee_repo = employee_repo
        self.authz_service = authz_service

    def get_timesheet_status(self, actor: EmployeeRecord, target_employee_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieves timesheet compliance status for an employee.
        """
        target_id = target_employee_id or actor.employee_id
        target = self.employee_repo.get_by_id(target_id)
        if not target:
            raise NotFoundError(f"Employee '{target_id}' not found.")

        # Authorize: Actor viewing target's timesheet
        self.authz_service.authorize(
            actor=actor,
            action=AuthAction.CHECK_TIMESHEET,
            target_employee=target,
            resource=f"TIMESHEET_{target.employee_id}",
        )

        records = self.operations_repo.get_timesheets(target.employee_id)
        if not records:
            return {
                "employee_id": target.employee_id,
                "has_pending": False,
                "status_summary": "All timesheets up to date.",
                "latest_record": None,
            }

        latest = records[0]
        has_action_needed = latest.status in (TimesheetStatus.PENDING, TimesheetStatus.OVERDUE)

        log_audit_event("TIMESHEET_LOOKUP", actor.employee_id, "GET_TIMESHEET", "ALLOWED", target.employee_id, {"status": latest.status.value})

        return {
            "employee_id": target.employee_id,
            "period": f"{latest.period_start} to {latest.period_end}",
            "hours_logged": latest.hours_logged,
            "status": latest.status.value,
            "due_date": latest.due_date,
            "action_required": has_action_needed,
            "message": (
                f"Your timesheet for week ending {latest.period_end} is currently {latest.status.value} "
                f"({latest.hours_logged} hours logged). Please submit before Friday 5:00 PM."
                if has_action_needed
                else f"Your timesheet for week ending {latest.period_end} is {latest.status.value}."
            ),
        }
