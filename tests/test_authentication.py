"""
Authentication Unit & Integration Tests (Phase B: Zero-Cost OIDC & Perimeter Security).
Verifies token presence, signature validation, mock token provider, identity mapping,
and strict ALLOWED_CORPORATE_DOMAIN perimeter enforcement.
"""

import pytest
from app.config import settings
from app.services.authentication_service import AuthenticationService
from app.services.employee_service import EmployeeService
from app.repositories.memory_repository import MemoryEmployeeRepository
from app.core.exceptions import AuthenticationError
from app.models import AuthenticatedPrincipal


def test_missing_authorization_header(client):
    """Verifies that requests without Authorization header receive 401 Unauthorized."""
    response = client.post("/api/v1/landing")
    assert response.status_code == 401
    assert "Missing Authorization header" in response.json()["message"]


def test_malformed_authorization_header(client):
    """Verifies that non-Bearer Authorization headers receive 401 Unauthorized."""
    response = client.post("/api/v1/landing", headers={"Authorization": "Basic dXNlcjpwYXNz"})
    assert response.status_code == 401
    assert "Malformed Authorization header" in response.json()["message"]


def test_invalid_mock_token(client):
    """Verifies that unknown mock tokens receive 401 Unauthorized."""
    response = client.post("/api/v1/landing", headers={"Authorization": "Bearer mock-invalid-token-999"})
    assert response.status_code == 401
    assert "Invalid mock Google token" in response.json()["message"]


def test_corporate_domain_perimeter_rejection(client):
    """
    PERIMETER SECURITY TEST:
    Verifies that requests originating outside ALLOWED_CORPORATE_DOMAIN
    are immediately dropped with 401 Unauthorized.
    """
    response = client.post(
        "/api/v1/landing",
        headers={"Authorization": "Bearer mock-google-token-unauthorized-domain"},
    )
    assert response.status_code == 401
    assert "Corporate perimeter violation" in response.json()["message"]


def test_custom_corporate_domain_check():
    """Verifies programmatic enforcement of custom corporate domain."""
    auth_service = AuthenticationService(auth_provider="mock_google", allowed_domain="enterprise.io")

    # Domain mismatch should raise AuthenticationError
    principal_bad = AuthenticatedPrincipal(
        subject="sub-123",
        email="user@gmail.com",
        issuer="https://accounts.google.com",
    )
    with pytest.raises(AuthenticationError) as exc:
        auth_service._enforce_corporate_domain(principal_bad)
    assert "Corporate perimeter violation" in str(exc.value)

    # Valid domain should pass cleanly
    principal_good = AuthenticatedPrincipal(
        subject="sub-123",
        email="rahul@enterprise.io",
        issuer="https://accounts.google.com",
        hosted_domain="enterprise.io",
    )
    auth_service._enforce_corporate_domain(principal_good)


def test_unregistered_google_subject_fails():
    """Verifies that a valid Google subject not present in the employee directory is rejected."""
    auth_service = AuthenticationService()
    emp_repo = MemoryEmployeeRepository()
    emp_service = EmployeeService(emp_repo)

    # Valid token structure with unknown subject
    principal = auth_service.authenticate_token("Bearer google-sub-unknown-9999")
    assert principal.subject == "google-sub-unknown-9999"

    with pytest.raises(AuthenticationError) as exc_info:
        emp_service.resolve_principal_to_employee(principal)
    assert "not registered in the employee directory" in str(exc_info.value)


def test_valid_google_identity_resolves_correct_employee(client, rahul_headers):
    """Verifies that a valid Google ID token maps to the correct internal EmployeeRecord."""
    response = client.post("/api/v1/landing", headers=rahul_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["employee_id"] == "EMP-2026-001"
    assert data["name"] == "Rahul Sharma"
    assert data["is_day_one"] is True
