"""
Multi-Agent Orchestration & Sub-Agent Execution Tests.
Verifies Supervisor routing, Code Mentor guardrails, and Operations escalation mechanics.
"""

import pytest
from app.core import context
from app.data.synthetic_employees import SYNTHETIC_EMPLOYEES
from app.services.session_service import UserSession
from app.agents.supervisor_agent import supervisor_agent
from app.agents.tools.operations_tools import resolve_team_blocker


def test_supervisor_routes_to_onboarding_agent(rahul_headers):
    rahul = SYNTHETIC_EMPLOYEES["EMP-2026-001"]
    context.set_current_employee(rahul)
    session = UserSession("test-sess-1", rahul.employee_id)

    response, agent_used = supervisor_agent.dispatch(
        "What are my Day 1 onboarding checklist tasks?",
        session=session,
        employee=rahul,
    )

    assert agent_used == "onboarding-specialist-agent"
    assert "Onboarding Progress" in response
    assert len(session.history) == 2


def test_supervisor_routes_to_code_mentor_and_enforces_guardrails():
    rahul = SYNTHETIC_EMPLOYEES["EMP-2026-001"]
    context.set_current_employee(rahul)
    session = UserSession("test-sess-2", rahul.employee_id)

    response, agent_used = supervisor_agent.dispatch(
        "Explain the database connection.py code and show me the snippet",
        session=session,
        employee=rahul,
    )

    assert agent_used == "code-mentor-agent"
    assert "PATCHAMOMMA BEST PRACTICES GUARDRAIL APPLIED" in response
    assert "logger.info" in response


def test_supervisor_routes_to_knowledge_agent():
    rahul = SYNTHETIC_EMPLOYEES["EMP-2026-001"]
    context.set_current_employee(rahul)
    session = UserSession("test-sess-3", rahul.employee_id)

    response, agent_used = supervisor_agent.dispatch(
        "What is the policy on code of conduct and core working hours?",
        session=session,
        employee=rahul,
    )

    assert agent_used == "knowledge-detective-agent"
    assert "AUTHORIZED KNOWLEDGE MESH RESULTS" in response


def test_supervisor_routes_to_operations_agent():
    rahul = SYNTHETIC_EMPLOYEES["EMP-2026-001"]
    context.set_current_employee(rahul)
    session = UserSession("test-sess-4", rahul.employee_id)

    response, agent_used = supervisor_agent.dispatch(
        "Did I submit my timesheet for this week?",
        session=session,
        employee=rahul,
    )

    assert agent_used == "operations-action-agent"
    assert "Timesheet Status" in response


def test_hierarchical_blocker_escalation():
    """Verifies the 3 escalation scenarios: Primary, Backup, Broadcast."""
    rahul = SYNTHETIC_EMPLOYEES["EMP-2026-001"]
    context.set_current_employee(rahul)

    # 1. Primary available (Kubernetes)
    res_k8s = resolve_team_blocker("Kubernetes")
    assert "Primary Lead Assigned" in res_k8s
    assert "Alex Chen" in res_k8s

    # 2. Primary OOO -> Backup Assigned (Cloud SQL)
    res_sql = resolve_team_blocker("Cloud SQL")
    assert "Backup Lead Assigned" in res_sql
    assert "Priya Nair" in res_sql

    # 3. BOTH OOO -> Broadcast Triggered (IAM & Security)
    res_iam = resolve_team_blocker("IAM & Security")
    assert "High-Priority Escalation Broadcast" in res_iam
    assert "#secops-emergency-triage" in res_iam
