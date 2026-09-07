"""
FastAPI Dependencies and Service Container.
Extracts authenticated identity, resolves internal EmployeeRecord, and sets execution ContextVars.
"""

from typing import Optional
from fastapi import Header, Depends, Query

from app.config import settings
from app.core import context
from app.core.exceptions import AuthenticationError
from app.models import EmployeeRecord, AuthenticatedPrincipal
from app.repositories.base import (
    IEmployeeRepository,
    IOnboardingRepository,
    IKnowledgeRepository,
    IOperationsRepository,
)
from app.repositories.memory_repository import (
    MemoryEmployeeRepository,
    MemoryOnboardingRepository,
    MemoryKnowledgeRepository,
    MemoryOperationsRepository,
)
from app.repositories.bigquery_repository import (
    BigQueryEmployeeRepository,
    BigQueryOnboardingRepository,
    BigQueryKnowledgeRepository,
    BigQueryOperationsRepository,
)
from app.services.authentication_service import AuthenticationService
from app.services.authorization_service import AuthorizationService
from app.services.employee_service import EmployeeService
from app.services.session_service import SessionService, UserSession, FirestoreSessionStore, MemorySessionStore
from app.services.onboarding_service import OnboardingService
from app.services.knowledge_service import KnowledgeService
from app.services.timesheet_service import TimesheetService
from app.services.incident_service import IncidentService
from app.services.proactive_service import ProactiveService


# ============================================================================
# SINGLETON REPOSITORIES & SERVICES FACTORY
# ============================================================================

def init_repositories():
    if settings.REPOSITORY_BACKEND == "bigquery":
        emp_repo = BigQueryEmployeeRepository()
        onb_repo = BigQueryOnboardingRepository()
        knw_repo = BigQueryKnowledgeRepository()
        ops_repo = BigQueryOperationsRepository()
    else:
        emp_repo = MemoryEmployeeRepository()
        onb_repo = MemoryOnboardingRepository(employee_repo=emp_repo)
        knw_repo = MemoryKnowledgeRepository()
        ops_repo = MemoryOperationsRepository()

    return emp_repo, onb_repo, knw_repo, ops_repo


# Initialize container singletons
_emp_repo, _onb_repo, _knw_repo, _ops_repo = init_repositories()

auth_service = AuthenticationService()
authz_service = AuthorizationService()
employee_service = EmployeeService(employee_repo=_emp_repo)
session_service = SessionService()
onboarding_service = OnboardingService(onboarding_repo=_onb_repo, employee_repo=_emp_repo, authz_service=authz_service)
knowledge_service = KnowledgeService(knowledge_repo=_knw_repo, authz_service=authz_service)
timesheet_service = TimesheetService(operations_repo=_ops_repo, employee_repo=_emp_repo, authz_service=authz_service)
incident_service = IncidentService(operations_repo=_ops_repo, authz_service=authz_service)
proactive_service = ProactiveService(onboarding_service=onboarding_service, timesheet_service=timesheet_service)


# ============================================================================
# FASTAPI AUTH DEPENDENCIES
# ============================================================================

def get_current_principal(authorization: Optional[str] = Header(None)) -> AuthenticatedPrincipal:
    """
    Validates Google Identity Bearer token from the incoming HTTP request.
    Enforces corporate domain perimeter boundaries.
    Raises 401 if missing or invalid.
    """
    principal = auth_service.authenticate_token(authorization)
    context.set_current_principal(principal)
    return principal


def get_current_employee(principal: AuthenticatedPrincipal = Depends(get_current_principal)) -> EmployeeRecord:
    """
    Maps the verified Google Subject to the internal trusted EmployeeRecord.
    Binds the employee to ContextVar for zero-trust tool access.
    """
    employee = employee_service.resolve_principal_to_employee(principal)
    context.set_current_employee(employee)
    return employee


def get_authenticated_session(
    session_id: Optional[str] = Query(None),
    current_employee: EmployeeRecord = Depends(get_current_employee),
) -> UserSession:
    """
    Retrieves or creates a session while strictly enforcing ownership by current_employee.
    Raises 403 Forbidden if attempting to hijack another employee's session.
    """
    return session_service.get_or_create_session(session_id, current_employee)
