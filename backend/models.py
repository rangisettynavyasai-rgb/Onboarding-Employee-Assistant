#!/usr/bin/env python3
"""
Patchamomma 2026: Core Python Data Models
Defines all schema types matching BigQuery tables in patchamomma-505416.employee_ai
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime, date

class AuthorizationRole(str, Enum):
    EMPLOYEE = "employee"
    MANAGER = "manager"
    HR = "hr"
    IT = "it"

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"

class TimesheetStatus(str, Enum):
    SUBMITTED = "SUBMITTED"
    PENDING = "PENDING"
    OVERDUE = "OVERDUE"
    APPROVED = "APPROVED"

class IncidentSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass
class EmployeeRecord:
    employee_id: str
    google_subject: str
    email: str
    name: str
    department: str
    team: str
    job_role: str
    authorization_role: AuthorizationRole
    manager_id: Optional[str] = None
    location: str = "HQ"
    joining_date: str = "2026-09-01"
    onboarding_status: str = "IN_PROGRESS"
    is_day_one: bool = False
    assigned_buddy_name: Optional[str] = None
    assigned_buddy_email: Optional[str] = None
    onboarding_track: str = "Backend"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "employee_id": self.employee_id,
            "google_subject": self.google_subject,
            "email": self.email,
            "name": self.name,
            "department": self.department,
            "team": self.team,
            "job_role": self.job_role,
            "authorization_role": self.authorization_role.value if isinstance(self.authorization_role, AuthorizationRole) else self.authorization_role,
            "manager_id": self.manager_id,
            "location": self.location,
            "joining_date": self.joining_date,
            "onboarding_status": self.onboarding_status,
            "is_day_one": self.is_day_one,
            "assigned_buddy_name": self.assigned_buddy_name,
            "assigned_buddy_email": self.assigned_buddy_email,
            "onboarding_track": self.onboarding_track,
        }

@dataclass
class OnboardingTask:
    task_id: str
    title: str
    description: str
    status: TaskStatus
    due_days_after_start: int
    due_date: str = ""
    is_overdue: bool = False
    completed_at: Optional[str] = None
    category: str = "General"
    action_link: Optional[str] = None

    def calculate_due(self, joining_date_str: str) -> None:
        try:
            join_dt = datetime.strptime(joining_date_str, "%Y-%m-%d")
            # Calculate due date: joining_date + due_days
            from datetime import timedelta
            due_dt = join_dt + timedelta(days=self.due_days_after_start)
            self.due_date = due_dt.strftime("%Y-%m-%d")
            # Overdue if not completed and current time is past due date
            # Today's reference: 2026-09-07
            today_str = "2026-09-07"
            if self.status != TaskStatus.COMPLETED and self.due_date < today_str:
                self.is_overdue = True
            else:
                self.is_overdue = False
        except Exception:
            self.due_date = f"+{self.due_days_after_start}d"
            self.is_overdue = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value if isinstance(self.status, TaskStatus) else self.status,
            "due_days_after_start": self.due_days_after_start,
            "due_date": self.due_date,
            "is_overdue": self.is_overdue,
            "completed_at": self.completed_at,
            "category": self.category,
            "action_link": self.action_link,
        }

@dataclass
class KnowledgeChunk:
    chunk_id: str
    document_id: str
    chunk_index: int
    content: str
    team: str
    access_level: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "content": self.content,
            "team": self.team,
            "access_level": self.access_level,
        }

@dataclass
class KnowledgeAsset:
    document_id: str
    title: str
    source: str
    gcs_uri: str
    team: str
    access_level: str
    document_type: str
    owner: str
    description: str
    chunks: List[KnowledgeChunk] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "title": self.title,
            "source": self.source,
            "gcs_uri": self.gcs_uri,
            "team": self.team,
            "access_level": self.access_level,
            "document_type": self.document_type,
            "owner": self.owner,
            "description": self.description,
            "chunks": [c.to_dict() for c in self.chunks],
        }

@dataclass
class TimesheetRecord:
    timesheet_id: str
    employee_id: str
    period_start: str
    period_end: str
    hours_logged: float
    status: TimesheetStatus
    due_date: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timesheet_id": self.timesheet_id,
            "employee_id": self.employee_id,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "hours_logged": self.hours_logged,
            "status": self.status.value if isinstance(self.status, TimesheetStatus) else self.status,
            "due_date": self.due_date,
        }

@dataclass
class IncidentRecord:
    incident_id: str
    created_by: str
    category: str
    summary: str
    severity: IncidentSeverity
    status: str
    assigned_team: str
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "created_by": self.created_by,
            "category": self.category,
            "summary": self.summary,
            "severity": self.severity.value if isinstance(self.severity, IncidentSeverity) else self.severity,
            "status": self.status,
            "assigned_team": self.assigned_team,
            "created_at": self.created_at,
        }
