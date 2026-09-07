"""
Agent Tool Zero-Trust & Context Injection Security Tests.
Verifies that agent tools execute for the authenticated context employee and cannot be spoofed by model arguments.
"""

import pytest
from app.core import context
from app.data.synthetic_employees import SYNTHETIC_EMPLOYEES
from app.agents.tools.onboarding_tools import get_my_onboarding_status, get_team_onboarding_progress
from app.agents.tools.operations_tools import check_my_timesheet_status


def test_tool_pulls_identity_from_context():
    """Verifies that calling get_my_onboarding_status() returns the context user's details."""
    rahul = SYNTHETIC_EMPLOYEES["EMP-2026-001"]
    context.set_current_employee(rahul)

    output = get_my_onboarding_status()
    assert "Rahul Sharma" in output
    assert "Payments Team" in output
    assert "Completed:" in output


def test_tool_fails_if_no_context_bound():
    """Verifies that invoking tools outside an authenticated context raises RuntimeError."""
    context._current_employee.set(None)

    with pytest.raises(RuntimeError) as exc_info:
        context.get_current_employee()
    assert "Zero-trust check failed" in str(exc_info.value)


def test_team_progress_tool_respects_manager_boundary():
    """Manager (Sarah) sees Payments team. Regular employee (Rahul) is denied."""
    sarah = SYNTHETIC_EMPLOYEES["EMP-2026-010"]  # Payments Manager
    context.set_current_employee(sarah)
    output_sarah = get_team_onboarding_progress()
    assert "Team Onboarding Rollup: Payments" in output_sarah
    assert "Sarah Jenkins" in output_sarah

    rahul = SYNTHETIC_EMPLOYEES["EMP-2026-001"]  # Regular Employee
    context.set_current_employee(rahul)
    output_rahul = get_team_onboarding_progress()
    assert "Authorization / Lookup Error" in output_rahul or "Forbidden" in output_rahul


def test_timesheet_tool_binds_caller():
    """Timesheet tool automatically looks up the active employee's records."""
    rahul = SYNTHETIC_EMPLOYEES["EMP-2026-001"]
    context.set_current_employee(rahul)

    ts_output = check_my_timesheet_status()
    assert "Timesheet Status for Rahul Sharma" in ts_output
    assert any(s in ts_output for s in ("PENDING", "SUBMITTED", "APPROVED", "OVERDUE"))
