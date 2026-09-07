"""
End-to-End FastAPI Endpoint HTTP Tests.
Verifies all REST and Chat endpoints using authenticated TestClients.
"""

import pytest


def test_health_probe(client):
    """Verifies Cloud Run health check returns 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["service"] == "patchamomma-onboarding-agent"


def test_proactive_landing_endpoint(client, rahul_headers):
    """Verifies proactive landing generates orientation package for Day-1 joiner."""
    response = client.post("/api/v1/landing", headers=rahul_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Rahul Sharma"
    assert "Day 1 Onboarding Kickoff" in data["proactive_greeting"]
    assert "Priya Nair" in data["proactive_greeting"]


def test_interactive_chat_endpoint(client, rahul_headers):
    """Verifies interactive multi-agent chat endpoint."""
    response = client.post(
        "/api/v1/chat",
        headers=rahul_headers,
        json={"message": "What is my next onboarding milestone?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["agent_invoked"] == "onboarding-specialist-agent"
    assert "session_id" in data
    assert len(data["response"]) > 10


def test_onboarding_my_status_and_complete_task(client, rahul_headers):
    """Verifies getting onboarding status and completing a task."""
    # 1. Get status
    res1 = client.get("/api/v1/onboarding/my-status", headers=rahul_headers)
    assert res1.status_code == 200
    data1 = res1.json()
    initial_completed = data1["completed_count"]
    target_task_id = data1["next_pending_task"]["task_id"] if data1.get("next_pending_task") else "TASK-001-ENV"

    # 2. Complete pending task
    res2 = client.post(
        "/api/v1/onboarding/complete-task",
        headers=rahul_headers,
        json={"task_id": target_task_id},
    )
    assert res2.status_code == 200
    updated_completed = res2.json()["completed_count"]
    assert updated_completed >= initial_completed


def test_knowledge_search_endpoint(client, rahul_headers):
    """Verifies knowledge search returns authorized assets."""
    response = client.get("/api/v1/knowledge/search?query=payments", headers=rahul_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["results_count"] > 0
    assert any(r["team"] in ("Payments", "ALL") for r in data["results"])


def test_timesheet_endpoint(client, rahul_headers):
    """Verifies timesheet lookup."""
    response = client.get("/api/v1/timesheets/my-status", headers=rahul_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["employee_id"] == "EMP-2026-001"
    assert data["status"] in ("PENDING", "SUBMITTED", "APPROVED", "OVERDUE")


def test_incident_creation_endpoint(client, rahul_headers):
    """Verifies IT incident creation endpoint."""
    response = client.post(
        "/api/v1/incidents/create",
        headers=rahul_headers,
        json={
            "category": "VPN / Network",
            "summary": "Cannot access staging Cloud SQL proxy from local machine",
            "severity": "MEDIUM",
            "confirmed": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["incident_id"].startswith("INC-2026-")
    assert data["created_by"] == "EMP-2026-001"
    assert data["status"] == "OPEN"
