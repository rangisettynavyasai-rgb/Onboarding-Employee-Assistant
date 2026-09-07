"""
Session Security & Anti-Hijacking Tests (Phase C: Firestore Session Store).
Verifies that conversational sessions are cryptographically bound to employee identity,
blocking cross-user token reuse and cross-tenant session hijacking.
"""

import pytest
from app.models import EmployeeRecord, AuthorizationRole, ActiveSessionState, ChatMessage
from app.services.session_service import SessionService, MemorySessionStore
from app.core.exceptions import SessionSecurityError


def test_session_ownership_success(client, rahul_headers):
    """Rahul starts a conversation and successfully resumes his own session."""
    # Step 1: Start chat
    res1 = client.post(
        "/api/v1/chat",
        headers=rahul_headers,
        json={"message": "What is my onboarding status?"},
    )
    assert res1.status_code == 200
    session_id = res1.json()["session_id"]
    assert session_id is not None

    # Step 2: Resume with same session ID
    res2 = client.post(
        f"/api/v1/chat?session_id={session_id}",
        headers=rahul_headers,
        json={"message": "Show me the next task again."},
    )
    assert res2.status_code == 200
    assert res2.json()["session_id"] == session_id


def test_cross_employee_session_hijack_denied(client, rahul_headers, maya_headers):
    """
    ANTI-HIJACKING TEST:
    Rahul starts session S1.
    Maya attempts to pass Rahul's session S1 in her chat request.
    Server MUST deny Maya with 403 Forbidden.
    """
    # 1. Rahul creates session
    res_rahul = client.post(
        "/api/v1/chat",
        headers=rahul_headers,
        json={"message": "Hello, this is Rahul's private onboarding session."},
    )
    rahul_session_id = res_rahul.json()["session_id"]

    # 2. Maya attempts to access Rahul's session
    res_maya = client.post(
        f"/api/v1/chat?session_id={rahul_session_id}",
        headers=maya_headers,
        json={"message": "Read previous conversation history."},
    )

    assert res_maya.status_code == 403
    assert "Session security violation" in res_maya.json()["message"]


def test_converse_gateway_session_anti_hijacking(client, rahul_headers, maya_headers):
    """
    Verifies that the direct /api/v1/assistant/converse endpoint also strictly enforces anti-hijacking.
    """
    # 1. Rahul initiates converse round
    res_rahul = client.post(
        "/api/v1/assistant/converse?user_prompt=What+is+my+next+task",
        headers=rahul_headers,
    )
    assert res_rahul.status_code == 200
    rahul_session_id = res_rahul.json()["session_id"]

    # 2. Maya attempts converse with Rahul's session_id
    res_maya = client.post(
        f"/api/v1/assistant/converse?session_id={rahul_session_id}&user_prompt=Show+me+everything",
        headers=maya_headers,
    )
    assert res_maya.status_code == 403
    assert "Session security violation" in res_maya.json()["message"]


def test_direct_session_service_anti_hijacking():
    """Unit test verifying SessionService raises SessionSecurityError when employee_id differs."""
    store = MemorySessionStore()
    svc = SessionService(store=store)

    emp_rahul = EmployeeRecord(
        employee_id="EMP-2026-001",
        google_subject="sub-1",
        email="rahul@company.com",
        name="Rahul",
        department="Engineering",
        team="Payments",
        job_role="Software Engineer",
        authorization_role=AuthorizationRole.EMPLOYEE,
    )
    emp_maya = EmployeeRecord(
        employee_id="EMP-2026-002",
        google_subject="sub-2",
        email="maya@company.com",
        name="Maya",
        department="Engineering",
        team="Platform",
        job_role="Intern",
        authorization_role=AuthorizationRole.EMPLOYEE,
    )

    sess = svc.get_or_create_session(None, emp_rahul)
    assert sess.employee_id == "EMP-2026-001"

    # Maya trying to access Rahul's session
    with pytest.raises(SessionSecurityError) as exc:
        svc.get_or_create_session(sess.session_id, emp_maya)
    assert "Session security violation" in str(exc.value)
