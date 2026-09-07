"""
Abstract Repository Interfaces.
Enables transparent switching between in-memory mock datasets and Google BigQuery/GCS in production.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from app.models import (
    EmployeeRecord,
    OnboardingChecklist,
    TeamMemberOnboardingProgress,
    KnowledgeAsset,
    KnowledgeChunk,
    AuthorizationRole,
    TimesheetRecord,
    IncidentRecord,
    TeamEscalationContact,
)


class IEmployeeRepository(ABC):
    @abstractmethod
    def get_by_google_subject(self, google_subject: str) -> Optional[EmployeeRecord]:
        pass

    @abstractmethod
    def get_by_id(self, employee_id: str) -> Optional[EmployeeRecord]:
        pass

    @abstractmethod
    def get_by_team(self, team: str) -> List[EmployeeRecord]:
        pass

    @abstractmethod
    def get_by_manager_id(self, manager_id: str) -> List[EmployeeRecord]:
        pass

    @abstractmethod
    def list_all(self) -> List[EmployeeRecord]:
        pass


class IOnboardingRepository(ABC):
    @abstractmethod
    def get_checklist(self, employee_id: str) -> Optional[OnboardingChecklist]:
        pass

    @abstractmethod
    def complete_task(self, employee_id: str, task_id: str) -> bool:
        pass

    @abstractmethod
    def get_team_progress(self, manager_id: str, team: str) -> List[TeamMemberOnboardingProgress]:
        pass


class IKnowledgeRepository(ABC):
    @abstractmethod
    def get_by_id(self, document_id: str) -> Optional[KnowledgeAsset]:
        pass

    @abstractmethod
    def search_authorized(self, query: str, user_team: str, user_role: AuthorizationRole) -> List[KnowledgeChunk]:
        pass


class IOperationsRepository(ABC):
    @abstractmethod
    def get_timesheets(self, employee_id: str) -> List[TimesheetRecord]:
        pass

    @abstractmethod
    def create_incident(self, incident: IncidentRecord) -> IncidentRecord:
        pass

    @abstractmethod
    def get_escalation_contact(self, domain: str) -> Optional[TeamEscalationContact]:
        pass

    @abstractmethod
    def stream_telemetry(self, payload: Dict[str, Any]) -> str:
        pass
