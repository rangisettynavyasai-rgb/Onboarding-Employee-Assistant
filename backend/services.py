#!/usr/bin/env python3
"""
Company AI Assistant: Enterprise Domain Services (Python)
Unified operation lifecycle service definitions.
"""
import os
import re
import json
import base64
import time
import sys
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from backend.models import (
    EmployeeRecord, AuthorizationRole, TaskStatus, OnboardingTask,
    TimesheetStatus, IncidentSeverity, IncidentRecord, KnowledgeChunk, KnowledgeAsset,
    UserSession
)
from backend.data import (
    EMPLOYEES, ONBOARDING_TASKS, TIMESHEETS, INCIDENTS, TEAM_DIRECTORY, KNOWLEDGE_CATALOG
)
from backend.auth_policy import AuthPolicy, is_manager_or_hr
from backend.firestore import firestore_db
import backend.state_store as state_store
from backend.bigquery_service import BigQueryService
from backend.gcs_service import GCSService
from backend.jira_service import JiraService
from backend.salesforce_service import SalesforceService
from backend.calendar_service import CalendarService

_EMPLOYEES: Dict[str, EmployeeRecord] = {emp_id: emp for emp_id, emp in EMPLOYEES.items()}
_INCIDENTS: List[IncidentRecord] = list(INCIDENTS)
KNOWLEDGE_BASE = KNOWLEDGE_CATALOG
_SESSIONS: Dict[str, Any] = {}

# Mutable timesheets store
_TIMESHEETS: Dict[str, List[Any]] = {emp_id: list(ts_list) for emp_id, ts_list in TIMESHEETS.items()}

# Mutable checklist store initialization
_CHECKLISTS: Dict[str, List[Any]] = {}
for emp_id, emp in EMPLOYEES.items():
    source_tasks = ONBOARDING_TASKS.get(emp_id) or ONBOARDING_TASKS.get("EMP-2026-001", [])
    emp_tasks = []
    for t in source_tasks:
        task_copy = OnboardingTask(
            task_id=t.task_id, title=t.title, description=t.description, status=t.status,
            due_days_after_start=t.due_days_after_start, due_date=t.due_date,
            is_overdue=t.is_overdue, completed_at=t.completed_at, category=t.category, action_link=t.action_link
        )
        task_copy.calculate_due(emp.joining_date)
        emp_tasks.append(task_copy)
    _CHECKLISTS[emp_id] = emp_tasks

MOCK_TOKEN_MAP: Dict[str, str] = {
    "mock-google-token-rahul": "EMP-2026-001", "mock-google-token-maya": "EMP-2026-002",
    "mock-google-token-liam": "EMP-2026-003", "mock-google-token-carlos": "EMP-2026-004",
    "mock-google-token-alex": "EMP-2026-005", "mock-google-token-priya": "EMP-2026-006",
    "mock-google-token-elena": "EMP-2026-007", "mock-google-token-marcus": "EMP-2026-008",
    "mock-google-token-amanda": "EMP-2026-009", "mock-google-token-sarah": "EMP-2026-010"
}
def format_clean_name(name: Optional[str], email: str) -> str:
    if name and not (name.startswith("eyJ") or name.startswith("ya29.") or (len(name) > 35 and " " not in name)):
        return name.strip()
    if email and "@" in email:
        local_part = email.split("@")[0]
        cleaned = re.sub(r"[._+\-]+", " ", local_part).title()
        return cleaned.strip()
    return "New Employee"

def create_default_tasks_for_employee(employee_id: str, joining_date: str = "2026-09-10", track: str = "General") -> List[OnboardingTask]:
    suffix = employee_id.split("-")[-1] if "-" in employee_id else employee_id[-3:]
    task_templates = [
        ("SEC", "Complete Corporate Security & Data Privacy Training", "Review corporate security policies, configure 2FA, and complete mandatory data privacy certification.", 1, "Security & Compliance", "https://learning.internal.company.com/courses/sec-2026"),
        ("ENV", "Configure Local Development Environment & Cloud Credentials", "Install and configure gcloud CLI, Docker, and establish workstation authentication.", 2, "Development Setup", "gs://patchamomma-505416-employee-ai-knowledge/runbooks/kubernetes_cluster_triage.md"),
        ("BUDDY", "Schedule Introductory 1:1 with Onboarding Buddy", "Connect with your assigned mentor for workspace orientation and team introduction.", 3, "Team Integration", None),
        ("REPO", "Clone Team Repositories & Review Architecture Blueprint", "Access project repositories and review core microservice architecture guidelines.", 5, "First Milestone", "https://github.com/company/payments-core"),
        ("TS", "Review Timesheet Workflow & Payroll Schedule", "Verify timesheet portal access and understand Friday 5:00 PM submission deadline.", 7, "Operations", None),
    ]
    tasks = []
    for code, title, desc, due_days, cat, link in task_templates:
        task = OnboardingTask(
            task_id=f"TASK-{suffix}-{code}",
            title=title,
            description=desc,
            status=TaskStatus.PENDING,
            due_days_after_start=due_days,
            category=cat,
            action_link=link
        )
        task.calculate_due(joining_date)
        tasks.append(task)
    return tasks

class AuthService:
    """Enterprise Identity & Token Resolution Service."""

    @staticmethod
    def authenticate_credentials(identity: str, password: Optional[str] = None) -> Optional[EmployeeRecord]:
        emp = AuthService.resolve_employee(identity)
        if not emp:
            # If domain is open (* allowed) and not found, auto-provision user
            clean_id = identity.strip().lower()
            if "@" in clean_id:
                return AuthService.signup_employee(email=clean_id, name="")
            return None
        return emp

    @staticmethod
    def resolve_employee(bearer_token_or_id: str) -> Optional[EmployeeRecord]:
        if not bearer_token_or_id:
            return None
        clean_token = bearer_token_or_id.replace("Bearer ", "").strip() if bearer_token_or_id.lower().startswith("bearer ") else bearer_token_or_id.strip()

        # 1. Check BigQuery
        try:
            bq_res = BigQueryService.get_employee(clean_token)
            if bq_res and isinstance(bq_res, list) and len(bq_res) > 0:
                bq_emp = bq_res[0]
                role_val = str(bq_emp.get("authorization_role", "employee")).lower()
                clean_name = format_clean_name(bq_emp.get("name"), bq_emp.get("email", ""))
                return EmployeeRecord(
                    employee_id=bq_emp.get("employee_id", clean_token),
                    google_subject=bq_emp.get("google_subject", ""),
                    email=bq_emp.get("email", ""),
                    name=clean_name,
                    department=bq_emp.get("department", "Engineering"),
                    team=bq_emp.get("team", "Unassigned"),
                    job_role=bq_emp.get("job_role", "Software Engineer"),
                    authorization_role=AuthorizationRole(role_val if role_val in ["employee", "manager", "hr", "it"] else "employee"),
                    manager_id=bq_emp.get("manager_id"),
                    location=bq_emp.get("location", "HQ"),
                    joining_date=str(bq_emp.get("joining_date", datetime.utcnow().strftime("%Y-%m-%d"))),
                    onboarding_status=bq_emp.get("onboarding_status", "NOT_STARTED"),
                    is_day_one=bool(bq_emp.get("is_day_one", True)),
                    assigned_buddy_name=bq_emp.get("assigned_buddy_name"),
                    assigned_buddy_email=bq_emp.get("assigned_buddy_email"),
                    onboarding_track=bq_emp.get("onboarding_track", "General")
                )
        except Exception as bq_err:
            print(f"[AuthService] BigQuery lookup notice: {bq_err}", file=sys.stderr)

        # 2. Check Firestore
        try:
            fs_emp = firestore_db.get_employee(clean_token)
            if fs_emp:
                role_val = str(fs_emp.get("authorization_role", "employee")).lower()
                clean_name = format_clean_name(fs_emp.get("name"), fs_emp.get("email", ""))
                return EmployeeRecord(
                    employee_id=fs_emp.get("employee_id", clean_token),
                    google_subject=fs_emp.get("google_subject", ""),
                    email=fs_emp.get("email", ""),
                    name=clean_name,
                    department=fs_emp.get("department", "Engineering"),
                    team=fs_emp.get("team", "Unassigned"),
                    job_role=fs_emp.get("job_role", "Software Engineer"),
                    authorization_role=AuthorizationRole(role_val if role_val in ["employee", "manager", "hr", "it"] else "employee"),
                    manager_id=fs_emp.get("manager_id"),
                    location=fs_emp.get("location", "HQ"),
                    joining_date=str(fs_emp.get("joining_date", datetime.utcnow().strftime("%Y-%m-%d"))),
                    onboarding_status=fs_emp.get("onboarding_status", "NOT_STARTED"),
                    is_day_one=bool(fs_emp.get("is_day_one", True)),
                    assigned_buddy_name=fs_emp.get("assigned_buddy_name"),
                    assigned_buddy_email=fs_emp.get("assigned_buddy_email"),
                    onboarding_track=fs_emp.get("onboarding_track", "General")
                )
        except Exception as fs_err:
            print(f"[AuthService] Firestore lookup notice: {fs_err}", file=sys.stderr)

        # 3. Check Mock Map
        if clean_token in MOCK_TOKEN_MAP:
            return _EMPLOYEES.get(MOCK_TOKEN_MAP[clean_token])

        # 4. Check in-memory store
        for emp in _EMPLOYEES.values():
            if emp.google_subject == clean_token or emp.employee_id == clean_token or emp.email.lower() == clean_token.lower():
                return emp

        return None

    @staticmethod
    def signup_employee(
        email: str,
        name: str = "",
        password: Optional[str] = "",
        department: str = "Engineering",
        team: str = "Unassigned",
        job_role: str = "Software Engineer",
        onboarding_track: str = "General"
    ) -> EmployeeRecord:
        """
        Signs up a new employee with sequential BigQuery ID (EMP-YYYY-NNN),
        unassigned team, and 0% onboarding status with fresh tasks.
        """
        email_clean = email.strip().lower()
        clean_name = format_clean_name(name, email_clean)

        # Check if user already exists
        existing = AuthService.resolve_employee(email_clean)
        if existing:
            if clean_name and (existing.name == "New Employee" or existing.name.startswith("eyJ") or existing.name.startswith("ya29.")):
                existing.name = clean_name
            return existing

        # Allocate incremental ID from BigQuery sequence (e.g. EMP-2026-011)
        new_id = BigQueryService.allocate_next_employee_id()
        today_str = datetime.utcnow().strftime("%Y-%m-%d")

        new_emp = EmployeeRecord(
            employee_id=new_id,
            google_subject=f"sub-{new_id.lower()}",
            email=email_clean,
            name=clean_name,
            department=department or "Engineering",
            team=team or "Unassigned",
            job_role=job_role or "Software Engineer",
            authorization_role=AuthorizationRole.EMPLOYEE,
            manager_id=None,
            location="HQ",
            joining_date=today_str,
            onboarding_status="NOT_STARTED",
            is_day_one=True,
            assigned_buddy_name=None,
            assigned_buddy_email=None,
            onboarding_track=onboarding_track or "General"
        )

        # Persist new employee to BigQuery
        try:
            BigQueryService.create_employee(new_emp.to_dict())
        except Exception as bq_err:
            print(f"[AuthService] BigQuery create_employee notice: {bq_err}", file=sys.stderr)

        # Generate fresh initial tasks (status: PENDING -> 0% progress)
        tasks = create_default_tasks_for_employee(new_id, today_str, new_emp.onboarding_track)
        try:
            BigQueryService.create_employee_tasks(new_id, [t.to_dict() for t in tasks])
        except Exception as bq_task_err:
            print(f"[AuthService] BigQuery create_employee_tasks notice: {bq_task_err}", file=sys.stderr)

        _EMPLOYEES[new_id] = new_emp
        _CHECKLISTS[new_id] = tasks
        firestore_db.save_employee(new_emp.to_dict())

        return new_emp

    @staticmethod
    def register_google_profile(email: str, name: str, sub: str = "") -> EmployeeRecord:
        """
        Authenticates or provisions a Google profile with clean name, incremental ID,
        and unassigned team.
        """
        email_clean = email.strip().lower()
        clean_name = format_clean_name(name, email_clean)

        # 1. Try BigQuery lookup
        try:
            bq_res = BigQueryService.get_employee(email_clean)
            if bq_res and isinstance(bq_res, list) and len(bq_res) > 0:
                bq_emp = bq_res[0]
                role_val = str(bq_emp.get("authorization_role", "employee")).lower()
                existing_name = bq_emp.get("name")
                resolved_name = clean_name if (clean_name and clean_name != "New Employee") else format_clean_name(existing_name, email_clean)
                emp = EmployeeRecord(
                    employee_id=bq_emp.get("employee_id", "EMP-2026-001"),
                    google_subject=sub or bq_emp.get("google_subject", ""),
                    email=email_clean,
                    name=resolved_name,
                    department=bq_emp.get("department", "Engineering"),
                    team=bq_emp.get("team", "Unassigned"),
                    job_role=bq_emp.get("job_role", "Software Engineer"),
                    authorization_role=AuthorizationRole(role_val if role_val in ["employee", "manager", "hr", "it"] else "employee"),
                    manager_id=bq_emp.get("manager_id"),
                    location=bq_emp.get("location", "HQ"),
                    joining_date=str(bq_emp.get("joining_date", datetime.utcnow().strftime("%Y-%m-%d"))),
                    onboarding_status=bq_emp.get("onboarding_status", "NOT_STARTED"),
                    is_day_one=bool(bq_emp.get("is_day_one", True)),
                    assigned_buddy_name=bq_emp.get("assigned_buddy_name"),
                    assigned_buddy_email=bq_emp.get("assigned_buddy_email"),
                    onboarding_track=bq_emp.get("onboarding_track", "General")
                )
                _EMPLOYEES[emp.employee_id] = emp
                firestore_db.save_employee(emp.to_dict())
                return emp
        except Exception as bq_err:
            print(f"[AuthService] BigQuery lookup notice in register_google_profile: {bq_err}", file=sys.stderr)

        # 2. Try in-memory lookup
        for emp in _EMPLOYEES.values():
            if emp.email.lower() == email_clean or (sub and emp.google_subject == sub):
                if clean_name and (emp.name == "New Employee" or emp.name.startswith("eyJ") or emp.name.startswith("ya29.")):
                    emp.name = clean_name
                firestore_db.save_employee(emp.to_dict())
                return emp

        # 3. Auto-provision new employee with incremental ID (e.g. EMP-2026-011)
        new_id = BigQueryService.allocate_next_employee_id()
        today_str = datetime.utcnow().strftime("%Y-%m-%d")

        new_emp = EmployeeRecord(
            employee_id=new_id,
            google_subject=sub or f"google-sub-{new_id.lower()}",
            email=email_clean,
            name=clean_name,
            department="Engineering",
            team="Unassigned",
            job_role="Software Engineer",
            authorization_role=AuthorizationRole.EMPLOYEE,
            manager_id=None,
            location="HQ",
            joining_date=today_str,
            onboarding_status="NOT_STARTED",
            is_day_one=True,
            assigned_buddy_name=None,
            assigned_buddy_email=None,
            onboarding_track="General"
        )

        try:
            BigQueryService.create_employee(new_emp.to_dict())
        except Exception as bq_err:
            print(f"[AuthService] BigQuery create_employee notice: {bq_err}", file=sys.stderr)

        tasks = create_default_tasks_for_employee(new_id, today_str, new_emp.onboarding_track)
        try:
            BigQueryService.create_employee_tasks(new_id, [t.to_dict() for t in tasks])
        except Exception as bq_task_err:
            print(f"[AuthService] BigQuery create_employee_tasks notice: {bq_task_err}", file=sys.stderr)

        _EMPLOYEES[new_id] = new_emp
        _CHECKLISTS[new_id] = tasks
        firestore_db.save_employee(new_emp.to_dict())
        return new_emp

class OnboardingService:
    """Onboarding Lifecycle, Tasks & Manager Team Rollup Service."""

    @staticmethod
    def get_checklist(employee_id: str) -> Optional[Dict[str, Any]]:
        tasks = _CHECKLISTS.get(employee_id)
        if not tasks:
            emp = _EMPLOYEES.get(employee_id)
            join_date = emp.joining_date if emp else datetime.utcnow().strftime("%Y-%m-%d")
            track = emp.onboarding_track if emp else "General"

            # Check BigQuery for existing tasks
            bq_tasks_raw = []
            try:
                bq_tasks_raw = BigQueryService.get_employee_tasks(employee_id)
            except Exception:
                pass

            if bq_tasks_raw:
                tasks = []
                for r in bq_tasks_raw:
                    stat_str = str(r.get("status", "PENDING")).upper()
                    try:
                        task_stat = TaskStatus(stat_str)
                    except ValueError:
                        task_stat = TaskStatus.PENDING
                    t = OnboardingTask(
                        task_id=str(r.get("task_id", "")),
                        title=str(r.get("title", "")),
                        description=str(r.get("description", "")),
                        status=task_stat,
                        due_days_after_start=int(r.get("due_days_after_start", 1) or 1),
                        completed_at=str(r.get("completed_at", "")) if r.get("completed_at") else None,
                        category=str(r.get("category", "General")),
                        action_link=r.get("action_link")
                    )
                    t.calculate_due(join_date)
                    tasks.append(t)
                _CHECKLISTS[employee_id] = tasks
            else:
                tasks = create_default_tasks_for_employee(employee_id, join_date, track)
                _CHECKLISTS[employee_id] = tasks
                try:
                    BigQueryService.create_employee_tasks(employee_id, [t.to_dict() for t in tasks])
                except Exception:
                    pass

        completed_ids = list(state_store.get_completed_task_ids(employee_id))
        try:
            bq_tasks = BigQueryService.get_employee_tasks(employee_id)
            for bqt in bq_tasks:
                if bqt.get("status") == "COMPLETED" and bqt.get("task_id"):
                    if bqt["task_id"] not in completed_ids:
                        completed_ids.append(bqt["task_id"])
        except Exception:
            pass

        for t in tasks:
            if t.task_id in completed_ids:
                t.status = TaskStatus.COMPLETED
                t.is_overdue = False

        completed_count = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        total_count = len(tasks)
        next_pending = next((t for t in tasks if t.status == TaskStatus.PENDING), None)

        return {
            "employee_id": employee_id,
            "total_count": total_count,
            "completed_count": completed_count,
            "next_pending_task": next_pending.to_dict() if next_pending else None,
            "tasks": [t.to_dict() for t in tasks],
        }

    @staticmethod
    def complete_task(employee_id: str, task_id: str) -> bool:
        state_store.mark_task_completed(employee_id, task_id)
        try:
            BigQueryService.update_task_status(employee_id, task_id, "COMPLETED")
        except Exception as bq_err:
            print(f"[OnboardingService] BigQuery task update notice: {bq_err}", file=sys.stderr)

        tasks = _CHECKLISTS.get(employee_id)
        if tasks:
            for t in tasks:
                if t.task_id == task_id:
                    t.status = TaskStatus.COMPLETED
                    t.completed_at = datetime.utcnow().isoformat() + "Z"
                    t.is_overdue = False

        try:
            completed_ids = state_store.get_completed_task_ids(employee_id)
            total = len(tasks) if tasks else 6
            if len(completed_ids) >= total:
                BigQueryService.update_employee_status(employee_id, "COMPLETED")
        except Exception as bq_status_err:
            print(f"[OnboardingService] BigQuery employee status update notice: {bq_status_err}", file=sys.stderr)

        return True

    @staticmethod
    def get_team_progress(manager: EmployeeRecord) -> Dict[str, Any]:
        direct_reports = [
            e for e in _EMPLOYEES.values() if e.manager_id == manager.employee_id or e.team == manager.team
        ]

        members_progress: List[Dict[str, Any]] = []
        for report in direct_reports:
            cl = OnboardingService.get_checklist(report.employee_id)
            completed = cl["completed_count"] if cl else 0
            total = cl["total_count"] if cl else 0
            pending_titles = [t["title"] for t in (cl["tasks"] if cl else []) if t["status"] != TaskStatus.COMPLETED.value]
            overdue_count = sum(1 for t in (cl["tasks"] if cl else []) if t.get("is_overdue"))
            pct = int((completed / total * 100)) if total > 0 else 0

            members_progress.append({
                "employee_id": report.employee_id, "name": report.name, "email": report.email, "team": report.team,
                "job_role": report.job_role, "joining_date": report.joining_date, "total_tasks": total,
                "completed_tasks": completed, "pending_tasks": pending_titles, "overdue_tasks": overdue_count, "progress_percentage": pct,
            })

        overall_pct = int(sum(m["progress_percentage"] for m in members_progress) / len(members_progress)) if members_progress else 0

        return {
            "manager_id": manager.employee_id, "manager_name": manager.name, "team_name": manager.team,
            "total_team_members": len(members_progress), "overall_progress_percentage": overall_pct, "members": members_progress,
        }
def get_all_employees_from_db() -> Dict[str, EmployeeRecord]:
    """Return the current employee directory directly from BigQuery."""
    result: Dict[str, EmployeeRecord] = {}
    for row in BigQueryService.get_all_employees():
        role_val = str(row.get("authorization_role", "employee")).lower()
        result[str(row.get("employee_id", ""))] = EmployeeRecord(
            employee_id=str(row.get("employee_id", "")),
            google_subject=str(row.get("google_subject", "")),
            email=str(row.get("email", "")),
            name=str(row.get("name", "")),
            department=str(row.get("department", "Engineering")),
            team=str(row.get("team", "Unassigned")),
            job_role=str(row.get("job_role", "Software Engineer")),
            authorization_role=AuthorizationRole(role_val if role_val in ["employee", "manager", "hr", "it"] else "employee"),
            manager_id=row.get("manager_id"),
            location=str(row.get("location", "HQ")),
            joining_date=str(row.get("joining_date", datetime.utcnow().strftime("%Y-%m-%d"))),
            onboarding_status=str(row.get("onboarding_status", "NOT_STARTED")),
            is_day_one=bool(row.get("is_day_one", True)),
            assigned_buddy_name=row.get("assigned_buddy_name"),
            assigned_buddy_email=row.get("assigned_buddy_email"),
            onboarding_track=str(row.get("onboarding_track", "General")),
        )
    return result

class OperationsService:
    """Operations: Timesheets, 3-Tier Escalation Directory, and Incident Creation."""

    @staticmethod
    def get_timesheet_status(employee_id: str) -> Dict[str, Any]:
        override = state_store.get_timesheet_override(employee_id)
        if override:
            return {
                "employee_id": employee_id, "period": "Current Cycle", "period_end": "2026-09-04",
                "hours_logged": override.get("hours_logged", 40.0), "status": override.get("status", "SUBMITTED"),
                "due_date": "2026-09-04", "action_required": False,
                "message": f"Your timesheet for week ending 2026-09-04 ({override.get('hours_logged', 40.0)} hrs) has been submitted.",
            }

        records = _TIMESHEETS.get(employee_id, [])
        if not records:
            return {
                "employee_id": employee_id, "period": "Current Cycle", "hours_logged": 40.0,
                "status": TimesheetStatus.APPROVED.value, "action_required": False, "message": "Your timesheet is fully approved.",
            }

        latest = records[0]
        status_val = latest.status.value if isinstance(latest.status, TimesheetStatus) else latest.status
        action_required = status_val in [TimesheetStatus.PENDING.value, TimesheetStatus.OVERDUE.value]

        msg = f"Your timesheet for week ending {latest.period_end} is {status_val}."
        if action_required:
            msg = f"Your timesheet for week ending {latest.period_end} is {status_val} ({latest.hours_logged} hrs). Submit before Friday 5:00 PM."

        return {
            "employee_id": employee_id, "period": f"{latest.period_start} to {latest.period_end}",
            "period_end": latest.period_end, "hours_logged": latest.hours_logged, "status": status_val,
            "due_date": latest.due_date, "action_required": action_required, "message": msg,
        }

    @staticmethod
    def submit_timesheet(employee_id: str, hours: float = 40.0, notes: str = "") -> Dict[str, Any]:
        emp = _EMPLOYEES.get(employee_id)
        emp_name = emp.name if emp else "Employee"
        sf_res = SalesforceService.sync_timesheet(employee_id=employee_id, employee_name=emp_name, hours=hours, notes=notes)
        salesforce_id = sf_res.get("salesforce_id", "")
        state_store.save_timesheet_submission(employee_id, hours, notes, salesforce_id)
        result = SalesforceService.get_status()
        result["salesforce_sync"] = sf_res
        result["salesforce_id"] = salesforce_id
        result["salesforce_url"] = sf_res.get("salesforce_url", "")
        print(result)
        return result

    @staticmethod
    def create_incident(actor: EmployeeRecord, category: str, summary: str, severity: IncidentSeverity = IncidentSeverity.MEDIUM) -> Dict[str, Any]:
        import random, string
        suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        incident_id = f"INC-2026-{suffix}"

        cat_lower = category.lower()
        assigned_team = "IT-Support"
        if any(term in cat_lower for term in ["sql", "database", "k8s", "cluster", "kubernetes"]):
            assigned_team = "Platform"
        elif any(term in cat_lower for term in ["iam", "security", "token", "permission"]):
            assigned_team = "Security"

        jira_res = JiraService.create_incident_issue(
            summary=summary, category=category, severity=severity.value if hasattr(severity, "value") else str(severity),
            employee_id=actor.employee_id, reporter_email=actor.email
        )

        record = IncidentRecord(
            incident_id=incident_id, created_by=actor.employee_id, category=category, summary=summary,
            severity=severity, status="OPEN", assigned_team=assigned_team, created_at=datetime.utcnow().isoformat() + "Z",
        )
        _INCIDENTS.append(record)
        rec_dict = record.to_dict()
        rec_dict["jira_key"] = jira_res.get("jira_key")
        rec_dict["jira_url"] = jira_res.get("jira_url")
        rec_dict["jira_sync"] = jira_res
        state_store.add_incident(rec_dict)
        return rec_dict

    @staticmethod
    def resolve_escalation(domain: str) -> Dict[str, Any]:
        contact = None
        for key, val in TEAM_DIRECTORY.items():
            if key.lower() in domain.lower() or domain.lower() in key.lower():
                contact = val
                break
        if not contact:
            return {
                "domain": domain, "status": "FALLBACK_GENERAL", "assigned_contact": "IT Service Desk",
                "channel": "#general-it-helpdesk", "message": f"Routed to general desk for '{domain}'.",
            }

        primary_ooo = contact.get("primary_on_vacation", False)
        backup_ooo = contact.get("backup_on_vacation", False)

        if not primary_ooo:
            return {
                "domain": contact["domain"], "status": "PRIMARY_ASSIGNED", "assigned_contact": f"{contact['primary_lead_name']} ({contact['primary_email']})",
                "channel": contact["general_channel"], "message": f"Assigned to Primary Lead: {contact['primary_lead_name']}.",
            }
        if not backup_ooo:
            return {
                "domain": contact["domain"], "status": "BACKUP_ASSIGNED", "assigned_contact": f"{contact['backup_lead_name']} ({contact['backup_email']})",
                "channel": contact["general_channel"], "message": f"Primary away. Routed to Backup Lead: {contact['backup_lead_name']}.",
            }
        return {
            "domain": contact["domain"], "status": "BOTH_OOO_BROADCAST_TRIGGERED", "assigned_contact": f"Broadcast Channel ({contact['general_channel']})",
            "channel": contact["general_channel"], "message": "Emergency Alert: Both domain leads are Out of Office.",
        }

    @staticmethod
    def get_points_of_contact(employee: EmployeeRecord, access_token: Optional[str] = None) -> Dict[str, Any]:
        # Human POCs are a shared company directory, not employee-specific hardcoded UI data.
        # Resolve the canonical contacts from the employees table so every employee sees the
        # same DB source of truth; Google Calendar is then used for live availability/OOO sync.
        db_employees = {}
        try:
            db_employees = {e.employee_id: e for e in get_all_employees_from_db()}
        except Exception as db_err:
            print(f"[OperationsService] Contact directory DB lookup notice: {db_err}", file=sys.stderr)

        def find_contact(*, email: str = "", job_terms: tuple = ()) -> Optional[EmployeeRecord]:
            email_l = email.lower()
            for e in db_employees.values():
                if email_l and e.email.lower() == email_l:
                    return e
            for e in db_employees.values():
                role_text = f"{e.job_role} {e.department} {e.team}".lower()
                if job_terms and all(term.lower() in role_text for term in job_terms):
                    return e
            return None

        # Stable company-wide contacts from DB. These fallbacks only cover local/offline mode.
        buddy = find_contact(email="priya.nair@company.com", job_terms=("staff", "engineer"))
        manager = find_contact(email="sarah.j@company.com", job_terms=("manager",))
        it_contact = find_contact(email="marcus.v@company.com", job_terms=("it",))
        hr_contact = find_contact(email="amanda.w@company.com", job_terms=("people",))

        calendar_status = CalendarService.get_out_of_office_status(access_token)
        calendar_by_email = {
            str(m.get("email", "")).lower(): m
            for m in calendar_status.get("team_members", [])
            if m.get("email")
        }

        def contact_dict(e: Optional[EmployeeRecord], fallback_name: str, fallback_email: str, role: str, scope: str, channel: str) -> Dict[str, Any]:
            name = e.name if e else fallback_name
            email = e.email if e else fallback_email
            cal = calendar_by_email.get(email.lower(), {})
            return {
                "id": e.employee_id if e else None,
                "name": name,
                "email": email,
                "role": e.job_role if e else role,
                "scope": scope,
                "channel": channel,
                "status": cal.get("status", "Available"),
                "calendar_synced": bool(cal.get("calendar_synced", calendar_status.get("synced_with_google", False))),
                "source": "BigQuery employees + Google Calendar",
            }

        domain_contacts = []
        for domain, info in TEAM_DIRECTORY.items():
            resolved = OperationsService.resolve_escalation(domain)
            domain_contacts.append({
                "domain": domain, "primary_lead": info["primary_lead_name"], "primary_email": info["primary_email"], "primary_ooo": info.get("primary_on_vacation", False),
                "backup_lead": info["backup_lead_name"], "backup_email": info["backup_email"], "backup_ooo": info.get("backup_on_vacation", False),
                "channel": info["general_channel"], "active_contact": resolved["assigned_contact"], "status": resolved["status"],
            })

        return {
            "employee_id": employee.employee_id, "name": employee.name, "calendar_integration": calendar_status,
            "buddy": contact_dict(buddy, "Priya Nair", "priya.nair@company.com", "Staff Software Engineer & Tech Lead", "Day-1 Guidance & Code walkthroughs", "#payments-dev"),
            "manager": contact_dict(manager, "Sarah Jenkins", "sarah.j@company.com", "Engineering Manager", "Check-ins & Approvals", "#eng-leadership"),
            "it_support": contact_dict(it_contact, "Marcus Vance", "marcus.v@company.com", "Lead IT Admin", "Hardware & IAM credentials", "#help-it"),
            "people_ops": contact_dict(hr_contact, "Amanda Walker", "amanda.w@company.com", "Senior People Ops Specialist", "Benefits & Workplace Policies", "#people-ops"),
            "domain_escalations": domain_contacts,
        }
class KnowledgeService:
    """Authorized Pre-Retrieval ACL Knowledge Mesh & Insights Service."""

    @staticmethod
    def search_authorized(actor: EmployeeRecord, query: str) -> List[KnowledgeChunk]:
        q = query.lower()
        results: List[KnowledgeChunk] = []
        is_mgr = is_manager_or_hr(actor.authorization_role)

        for asset in KNOWLEDGE_BASE:
            if asset.access_level == "manager" and not is_mgr:
                continue
            if asset.team != "ALL" and asset.team.lower() != actor.team.lower():
                continue

            words = [w for w in q.split() if len(w) > 2]
            for chunk in asset.chunks:
                matches = (
                    asset.title.lower() in q or q in asset.title.lower() or q in chunk.content.lower()
                    or any(w in asset.title.lower() or w in chunk.content.lower() for w in words)
                )
                if matches:
                    results.append(chunk)
        return results

    @staticmethod
    def format_context(actor: EmployeeRecord, chunks: List[KnowledgeChunk], query: Optional[str] = None) -> str:
        perimeter = f"[ENFORCED_SECURITY_PERIMETER: employee_id={actor.employee_id} | team={actor.team} | clearance={actor.authorization_role}]"
        if not chunks:
            return f"{perimeter}\nNo authorized company knowledge assets matched your query."

        lines = [perimeter]
        for i, chunk in enumerate(chunks):
            lines.append(f"--- [AUTHORIZED ASSET {i + 1} ---\n{chunk.content}\n")
        return "\n".join(lines)

    @staticmethod
    def get_authorized_insights(actor: EmployeeRecord) -> List[Dict[str, Any]]:
        is_mgr = is_manager_or_hr(actor.authorization_role)
        results = []
        for asset in KNOWLEDGE_CATALOG:
            if asset.access_level == "manager" and not is_mgr:
                continue
            if asset.team != "ALL" and asset.team.lower() != actor.team.lower():
                continue
            first_chunk = asset.chunks[0].content if asset.chunks else ""
            summary_text = asset.description or (first_chunk[:140] + "..." if len(first_chunk) > 140 else first_chunk)
            results.append({
                "title": asset.title,
                "category": asset.document_type or "Runbook",
                "summary": summary_text,
                "team": asset.team,
                "access_level": asset.access_level,
                "effective_date": "2026-09-01",
                "highlight_tag": "SECURITY" if "iam" in asset.title.lower() or "proxy" in asset.title.lower() else ("CRITICAL" if "triage" in asset.title.lower() else "POLICY"),
                "action_suggestion": f"View {asset.title}"
            })
        return results[:6]

    @staticmethod
    def get_document(actor: EmployeeRecord, doc_id: str) -> Optional[Dict[str, Any]]:
        is_mgr = is_manager_or_hr(actor.authorization_role)
        for asset in KNOWLEDGE_CATALOG:
            if asset.document_id.lower() == doc_id.lower() or asset.title.lower() == doc_id.lower():
                if asset.access_level == "manager" and not is_mgr:
                    return {"error": "Unauthorized: Manager clearance required."}
                if asset.team != "ALL" and asset.team.lower() != actor.team.lower():
                    return {"error": f"Unauthorized: Restricted to {asset.team} team."}

                d = asset.to_dict()
                gcs_res = GCSService.read_document_from_gcs(asset.gcs_uri)
                d["full_content"] = gcs_res["content"] if gcs_res.get("content") else "\n\n".join(c.content for c in asset.chunks)
                d["source"] = "Google Cloud Storage (GCS Client)" if gcs_res.get("content") else "Knowledge Catalog"
                d["gcs_status"] = gcs_res.get("status", "GCS_OFFLINE")
                return d
        return None

    @staticmethod
    def get_all_documents(actor: EmployeeRecord) -> List[Dict[str, Any]]:
        is_mgr = is_manager_or_hr(actor.authorization_role)
        results = []
        for asset in KNOWLEDGE_CATALOG:
            if asset.access_level == "manager" and not is_mgr:
                continue
            if asset.team != "ALL" and asset.team.lower() != actor.team.lower():
                continue
            d = asset.to_dict()
            d["full_content"] = "\n\n".join(c.content for c in asset.chunks)
            results.append(d)
        return results


class ProactiveService:
    """Proactive Day-1 Onboarding Landing Generator."""

    @staticmethod
    def generate_landing(employee: EmployeeRecord) -> Dict[str, Any]:
        checklist = OnboardingService.get_checklist(employee.employee_id)
        timesheet_info = OperationsService.get_timesheet_status(employee.employee_id)
        greeting = f"Welcome back, {employee.name}! Weekly timesheets are due Friday by 5:00 PM."
        if employee.is_day_one:
            team_phrase = f" with {employee.team}" if employee.team and employee.team.strip().lower() != "unassigned" else ""
            greeting = f"Welcome to the team, {employee.name}! Glad to have you{team_phrase} as {employee.job_role}."

        return {
            "employee_id": employee.employee_id, "name": employee.name, "department": employee.department,
            "team": employee.team, "job_role": employee.job_role, "authorization_role": employee.authorization_role,
            "is_day_one": employee.is_day_one, "proactive_greeting": greeting, "onboarding_summary": checklist, "timesheet_status": timesheet_info,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }


class SessionService:
    """Conversational Session Management & Turn Persistence backed by Google Cloud Firestore and Enterprise DB."""

    @staticmethod
    def get_or_create_session(employee_id: str, session_id: Optional[str] = None) -> UserSession:
        from backend.models import UserSession
        canonical_id = f"sess-{employee_id.lower()}"
        if session_id and session_id.lower().startswith(canonical_id):
            effective_id = session_id.lower()
        else:
            effective_id = canonical_id
        
        try:
            fs_record = firestore_db.get_session(effective_id)
            if fs_record and fs_record.get("employee_id") == employee_id:
                return UserSession(
                    session_id=effective_id, employee_id=employee_id,
                    created_at=fs_record.get("created_at", datetime.utcnow().isoformat() + "Z"),
                    last_accessed_at=datetime.utcnow().isoformat() + "Z", history=fs_record.get("history", [])
                )
        except Exception:
            pass

        now = datetime.utcnow().isoformat() + "Z"
        ns = UserSession(session_id=effective_id, employee_id=employee_id, created_at=now, last_accessed_at=now, history=[])
        SessionService.save_session(ns)
        return ns

    @staticmethod
    def save_session(session: Any) -> None:
        session.last_accessed_at = datetime.utcnow().isoformat() + "Z"
        try:
            firestore_db.save_session(session.session_id, session.employee_id, session.history)
        except Exception:
            pass

    @staticmethod
    def append_message(session_id: str, employee_id: str, role: str, content: str, agent: Optional[str] = None) -> Any:
        session = SessionService.get_or_create_session(employee_id, session_id)
        session.history.append({"role": role, "content": content, "agent": agent, "timestamp": datetime.utcnow().isoformat() + "Z"})
        SessionService.save_session(session)
        return session
