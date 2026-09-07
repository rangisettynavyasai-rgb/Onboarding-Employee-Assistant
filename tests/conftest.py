"""
Pytest Configuration & Shared Fixtures.
Provides mock tokens and FastAPI TestClients for all representative employee personas.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.data.synthetic_employees import SYNTHETIC_EMPLOYEES
from app.models import EmployeeRecord


@pytest.fixture
def client():
    """Returns a FastAPI TestClient."""
    return TestClient(app)


# Persona Bearer Token Headers
@pytest.fixture
def rahul_headers():
    """Rahul Sharma: Day-1 Payments Software Engineer I (Employee Role)"""
    return {"Authorization": "Bearer mock-google-token-rahul"}


@pytest.fixture
def maya_headers():
    """Maya Lin: Day-1 Platform Cloud Infrastructure Intern (Employee Role)"""
    return {"Authorization": "Bearer mock-google-token-maya"}


@pytest.fixture
def liam_headers():
    """Liam Vance: Payments Software Engineer II (Employee Role)"""
    return {"Authorization": "Bearer mock-google-token-liam"}


@pytest.fixture
def carlos_headers():
    """Carlos Santana: Senior Staff Data Engineer (Employee Role)"""
    return {"Authorization": "Bearer mock-google-token-carlos"}


@pytest.fixture
def sarah_headers():
    """Sarah Jenkins: Engineering Manager - Payments (Manager Role)"""
    return {"Authorization": "Bearer mock-google-token-sarah"}


@pytest.fixture
def alex_headers():
    """Alex Chen: Director of Platform Engineering (Manager Role)"""
    return {"Authorization": "Bearer mock-google-token-alex"}


@pytest.fixture
def amanda_headers():
    """Amanda Walker: Senior People Ops Specialist (HR Role)"""
    return {"Authorization": "Bearer mock-google-token-amanda"}


@pytest.fixture
def marcus_headers():
    """Marcus Vance: Lead IT Systems Administrator (IT Role)"""
    return {"Authorization": "Bearer mock-google-token-marcus"}
