"""
Authorization & RBAC Security Tests.
Tests permission matrices for Employee, Manager, HR, and IT roles.
"""

import pytest
from app.services.authorization_service import AuthorizationService
from app.models import AuthAction, AuthorizationRole
from app.data.synthetic_employees import SYNTHETIC_EMPLOYEES
from app.core.exceptions import AuthorizationError


@pytest.fixture
def authz():
    return AuthorizationService()


def test_employee_can_view_own_profile(authz):
    rahul = SYNTHETIC_EMPLOYEES["EMP-2026-001"]
    assert authz.authorize(actor=rahul, action=AuthAction.VIEW_OWN_PROFILE, target_employee=rahul) is True


def test_employee_cannot_view_other_employee_private_onboarding(authz):
    rahul = SYNTHETIC_EMPLOYEES["EMP-2026-001"]
    carlos = SYNTHETIC_EMPLOYEES["EMP-2026-004"]
    with pytest.raises(AuthorizationError):
        authz.authorize(actor=rahul, action=AuthAction.VIEW_EMPLOYEE_ONBOARDING, target_employee=carlos)


def test_manager_can_view_direct_subordinate_onboarding(authz):
    sarah = SYNTHETIC_EMPLOYEES["EMP-2026-010"]  # Manager of Payments
    rahul = SYNTHETIC_EMPLOYEES["EMP-2026-001"]  # Subordinate
    assert authz.authorize(actor=sarah, action=AuthAction.VIEW_EMPLOYEE_ONBOARDING, target_employee=rahul) is True


def test_manager_cannot_view_unrelated_team_subordinate_onboarding(authz):
    sarah = SYNTHETIC_EMPLOYEES["EMP-2026-010"]  # Payments Manager
    carlos = SYNTHETIC_EMPLOYEES["EMP-2026-004"]  # DataOps Senior Staff
    with pytest.raises(AuthorizationError):
        authz.authorize(actor=sarah, action=AuthAction.VIEW_EMPLOYEE_ONBOARDING, target_employee=carlos)


def test_manager_can_view_team_progress_endpoint(client, sarah_headers):
    """Sarah (Manager) can view team onboarding rollup."""
    response = client.get("/api/v1/onboarding/team-progress", headers=sarah_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["manager_id"] == "EMP-2026-010"
    assert data["team_name"] == "Payments"
    assert len(data["members"]) >= 2


def test_regular_employee_cannot_view_team_progress_endpoint(client, rahul_headers):
    """Rahul (Regular Employee) is denied access (403) to team progress."""
    response = client.get("/api/v1/onboarding/team-progress", headers=rahul_headers)
    assert response.status_code == 403
    assert "not authorized" in response.json()["message"].lower()


def test_hr_can_update_onboarding(authz):
    amanda = SYNTHETIC_EMPLOYEES["EMP-2026-009"]  # HR
    rahul = SYNTHETIC_EMPLOYEES["EMP-2026-001"]
    assert authz.authorize(actor=amanda, action=AuthAction.UPDATE_EMPLOYEE_ONBOARDING, target_employee=rahul) is True


def test_it_can_manage_permissions(authz):
    marcus = SYNTHETIC_EMPLOYEES["EMP-2026-008"]  # IT
    rahul = SYNTHETIC_EMPLOYEES["EMP-2026-001"]   # Employee

    assert authz.authorize(actor=marcus, action=AuthAction.MANAGE_PERMISSIONS) is True
    with pytest.raises(AuthorizationError):
        authz.authorize(actor=rahul, action=AuthAction.MANAGE_PERMISSIONS)
