"""
High-Fidelity In-Memory Repository Implementation.
Provides deterministic, zero-external-dependency data access for unit testing and local development.
"""

import copy
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from app.models import (
    EmployeeRecord,
    OnboardingChecklist,
    OnboardingTask,
    TeamMemberOnboardingProgress,
    KnowledgeAsset,
    KnowledgeChunk,
    AuthorizationRole,
    AccessLevel,
    TaskStatus,
    TimesheetRecord,
    IncidentRecord,
    TeamEscalationContact,
)
from app.repositories.base import (
    IEmployeeRepository,
    IOnboardingRepository,
    IKnowledgeRepository,
    IOperationsRepository,
)
from app.data.synthetic_employees import SYNTHETIC_EMPLOYEES
from app.data.synthetic_onboarding import SYNTHETIC_ONBOARDING_CHECKLISTS
from app.data.synthetic_knowledge import SYNTHETIC_KNOWLEDGE_CATALOG
from app.data.synthetic_operations import (
    SYNTHETIC_TIMESHEETS,
    SYNTHETIC_INCIDENTS,
    SYNTHETIC_TEAM_DIRECTORY,
)

logger = logging.getLogger("patchamomma.repository.memory")


class MemoryEmployeeRepository(IEmployeeRepository):
    def __init__(self):
        self._employees: Dict[str, EmployeeRecord] = copy.deepcopy(SYNTHETIC_EMPLOYEES)

    def get_by_google_subject(self, google_subject: str) -> Optional[EmployeeRecord]:
        for emp in self._employees.values():
            if emp.google_subject == google_subject:
                return emp
        return None

    def get_by_id(self, employee_id: str) -> Optional[EmployeeRecord]:
        return self._employees.get(employee_id)

    def get_by_team(self, team: str) -> List[EmployeeRecord]:
        return [emp for emp in self._employees.values() if emp.team.lower() == team.lower()]

    def get_by_manager_id(self, manager_id: str) -> List[EmployeeRecord]:
        return [emp for emp in self._employees.values() if emp.manager_id == manager_id]

    def list_all(self) -> List[EmployeeRecord]:
        return list(self._employees.values())


class MemoryOnboardingRepository(IOnboardingRepository):
    def __init__(self, employee_repo: IEmployeeRepository):
        self._checklists: Dict[str, OnboardingChecklist] = copy.deepcopy(SYNTHETIC_ONBOARDING_CHECKLISTS)
        self._employee_repo = employee_repo

    def get_checklist(self, employee_id: str) -> Optional[OnboardingChecklist]:
        return self._checklists.get(employee_id)

    def complete_task(self, employee_id: str, task_id: str) -> bool:
        checklist = self._checklists.get(employee_id)
        if not checklist:
            return False

        found = False
        for task in checklist.tasks:
            if task.task_id == task_id:
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now(timezone.utc).isoformat()
                found = True
                break

        if found:
            checklist.completed_count = sum(1 for t in checklist.tasks if t.status == TaskStatus.COMPLETED)
            checklist.next_pending_task = next((t for t in checklist.tasks if t.status == TaskStatus.PENDING), None)
            return True
        return False

    def get_team_progress(self, manager_id: str, team: str) -> List[TeamMemberOnboardingProgress]:
        # Fetch direct reports belonging to this manager or team
        team_members = self._employee_repo.get_by_manager_id(manager_id)
        if not team_members:
            team_members = self._employee_repo.get_by_team(team)

        progress_list: List[TeamMemberOnboardingProgress] = []
        for member in team_members:
            checklist = self._checklists.get(member.employee_id)
            if checklist:
                pending_titles = [t.title for t in checklist.tasks if t.status != TaskStatus.COMPLETED]
                progress_list.append(
                    TeamMemberOnboardingProgress(
                        employee_id=member.employee_id,
                        name=member.name,
                        job_role=member.job_role,
                        team=member.team,
                        completed_count=checklist.completed_count,
                        total_count=checklist.total_count,
                        pending_tasks=pending_titles,
                        is_blocked=any(t.status == TaskStatus.BLOCKED for t in checklist.tasks),
                    )
                )
            else:
                progress_list.append(
                    TeamMemberOnboardingProgress(
                        employee_id=member.employee_id,
                        name=member.name,
                        job_role=member.job_role,
                        team=member.team,
                        completed_count=1,
                        total_count=1,
                        pending_tasks=[],
                        is_blocked=False,
                    )
                )
        return progress_list


class MemoryKnowledgeRepository(IKnowledgeRepository):
    def __init__(self):
        self._catalog: Dict[str, KnowledgeAsset] = copy.deepcopy(SYNTHETIC_KNOWLEDGE_CATALOG)

    def get_by_id(self, document_id: str) -> Optional[KnowledgeAsset]:
        return self._catalog.get(document_id)

    def search_authorized(self, query: str, user_team: str, user_role: AuthorizationRole) -> List[KnowledgeChunk]:
        """
        PRE-RETRIEVAL ACL ENFORCEMENT:
        Filters knowledge chunks strictly by caller's team domain and authorization role
        BEFORE ranking or returning chunks.
        """
        query_terms = query.lower().split()
        matched_chunks: List[KnowledgeChunk] = []

        for asset in self._catalog.values():
            # 1. Team Domain Gate
            team_match = False
            if asset.team == "ALL":
                team_match = True
            elif asset.team.lower() == user_team.lower():
                team_match = True
            elif user_role == AuthorizationRole.HR and asset.team == "HR":
                team_match = True
            elif user_role == AuthorizationRole.IT and asset.team == "IT":
                team_match = True

            if not team_match:
                continue

            # 2. Access Level Clearance Gate
            role_cleared = False
            if asset.access_level == AccessLevel.EMPLOYEE:
                role_cleared = True
            elif asset.access_level == AccessLevel.MANAGER and user_role in (AuthorizationRole.MANAGER,):
                role_cleared = True
            elif asset.access_level == AccessLevel.HR and user_role in (AuthorizationRole.HR,):
                role_cleared = True
            elif asset.access_level == AccessLevel.IT and user_role in (AuthorizationRole.IT,):
                role_cleared = True

            if not role_cleared:
                continue

            # 3. Text/Keyword matching on authorized chunks
            for chunk in asset.chunks:
                chunk_text = (chunk.content + " " + asset.title + " " + asset.description).lower()
                if not query_terms or any(term in chunk_text for term in query_terms):
                    matched_chunks.append(chunk)

        return matched_chunks


class MemoryOperationsRepository(IOperationsRepository):
    def __init__(self):
        self._timesheets: Dict[str, List[TimesheetRecord]] = copy.deepcopy(SYNTHETIC_TIMESHEETS)
        self._incidents: List[IncidentRecord] = copy.deepcopy(SYNTHETIC_INCIDENTS)
        self._directory: Dict[str, TeamEscalationContact] = copy.deepcopy(SYNTHETIC_TEAM_DIRECTORY)
        self._telemetry_log: List[Dict[str, Any]] = []

    def get_timesheets(self, employee_id: str) -> List[TimesheetRecord]:
        return self._timesheets.get(employee_id, [])

    def create_incident(self, incident: IncidentRecord) -> IncidentRecord:
        self._incidents.append(incident)
        return incident

    def get_escalation_contact(self, domain: str) -> Optional[TeamEscalationContact]:
        normalized = domain.strip().lower()
        if normalized in self._directory:
            return self._directory[normalized]
        for key, val in self._directory.items():
            if key in normalized or normalized in key:
                return val
        return None

    def stream_telemetry(self, payload: Dict[str, Any]) -> str:
        self._telemetry_log.append(payload)
        logger.info(f"[TELEMETRY STREAM] {json.dumps(payload)}")
        return payload.get("log_id", str(uuid.uuid4()))
