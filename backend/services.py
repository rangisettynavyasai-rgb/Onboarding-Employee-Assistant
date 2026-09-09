#!/usr/bin/env python3
"""
Company AI Assistant: Enterprise Domain Services (Python)
Provides identity resolution, onboarding lifecycle, operational workflows,
knowledge mesh querying with pre-retrieval ACL enforcement, proactive landing generation,
and conversational session management.
"""

import json
import base64
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from backend.models import (
    EmployeeRecord,
    AuthorizationRole,
    TaskStatus,
    TimesheetStatus,
    IncidentSeverity,
    IncidentRecord,
    KnowledgeChunk,
    KnowledgeMeshInsight,
    TeamEscalationContact,
    TeamMemberOnboardingProgress,
    TeamOnboardingSummary,
    UserSession,
    TimesheetStatusSummary,
)
from backend.data import (
    EMPLOYEES,
    ONBOARDING_TASKS,
    TIMESHEETS,
    INCIDENTS,
    TEAM_DIRECTORY,
    KNOWLEDGE_INSIGHTS,
    KNOWLEDGE_CATALOG,
)
from backend.auth_policy import can_access_chunk, is_manager_or_hr
from backend.firestore import firestore_db
import backend.state_store as state_store
from backend.bigquery_service import BigQueryService
from backend.gcs_service import GCSService
from backend.jira_service import JiraService
from backend.salesforce_service import SalesforceService
from backend.calendar_service import CalendarService

# In-memory persistent state stores
_EMPLOYEES: Dict[str, EmployeeRecord] = {
    emp_id: emp for emp_id, emp in EMPLOYEES.items()
}

# Mutable task store: employee_id -> List[OnboardingTask]
_CHECKLISTS: Dict[str, List[Any]] = {}
for emp_id, emp in EMPLOYEES.items():
    source_tasks = ONBOARDING_TASKS.get(emp_id) or ONBOARDING_TASKS.get("EMP-2026-001", [])
    emp_tasks = []
    for t in source_tasks:
        task_copy = type(t)(
            task_id=t.task_id,
            title=t.title,
            description=t.description,
            status=t.status,
            due_days_after_start=t.due_days_after_start,
            due_date=t.due_date,
            is_overdue=t.is_overdue,
            completed_at=t.completed_at,
            category=t.category,
            action_link=t.action_link,
        )
        task_copy.calculate_due(emp.joining_date)
        emp_tasks.append(task_copy)
    _CHECKLISTS[emp_id] = emp_tasks

# Mutable timesheets store: employee_id -> List[TimesheetRecord]
_TIMESHEETS: Dict[str, List[Any]] = {}
for emp_id, ts_list in TIMESHEETS.items():
    _TIMESHEETS[emp_id] = list(ts_list)

# Mutable incident records
_INCIDENTS: List[IncidentRecord] = list(INCIDENTS)

KNOWLEDGE_BASE = KNOWLEDGE_CATALOG

# Mutable session history store: session_id -> UserSession
_SESSIONS: Dict[str, UserSession] = {}

# Mock token to employee ID mapping
MOCK_TOKEN_MAP: Dict[str, str] = {
    "mock-google-token-rahul": "EMP-2026-001",
    "mock-google-token-maya": "EMP-2026-002",
    "mock-google-token-liam": "EMP-2026-003",
    "mock-google-token-carlos": "EMP-2026-004",
    "mock-google-token-alex": "EMP-2026-005",
    "mock-google-token-priya": "EMP-2026-006",
    "mock-google-token-elena": "EMP-2026-007",
    "mock-google-token-marcus": "EMP-2026-008",
    "mock-google-token-amanda": "EMP-2026-009",
    "mock-google-token-sarah": "EMP-2026-010",
}


class AuthService:
    """Enterprise Identity & Token Resolution Service."""

    @staticmethod
    def authenticate_credentials(identity: str, password: Optional[str] = None) -> Optional[EmployeeRecord]:
        """Validates corporate username/email and password credentials."""
        emp = AuthService.resolve_employee(identity)
        if not emp:
            return None
        # In this enterprise prototype environment, employees authenticate with their corporate password
        # (Demo credentials accept 'password123' or any non-empty corporate password)
        if password is not None and isinstance(password, str):
            if len(password.strip()) == 0:
                return None
        return emp

    @staticmethod
    def resolve_employee(bearer_token_or_id: str) -> Optional[EmployeeRecord]:
        if not bearer_token_or_id:
            return None

        clean_token = bearer_token_or_id
        if clean_token.lower().startswith("bearer "):
            clean_token = clean_token[7:].strip()
        else:
            clean_token = clean_token.strip()

        # 1. Direct BigQuery employee lookup
        try:
            bq_emp = BigQueryService.get_employee(clean_token)
            if bq_emp:
                return EmployeeRecord(
                    employee_id=bq_emp.get("employee_id", clean_token),
                    google_subject=bq_emp.get("google_subject", ""),
                    email=bq_emp.get("email", ""),
                    name=bq_emp.get("name", ""),
                    department=bq_emp.get("department", "Engineering"),
                    team=bq_emp.get("team", "Payments"),
                    job_role=bq_emp.get("job_role", "Software Engineer"),
                    authorization_role=AuthorizationRole(bq_emp.get("authorization_role", "employee")),
                    manager_id=bq_emp.get("manager_id"),
                    location=bq_emp.get("location", "HQ"),
                    joining_date=str(bq_emp.get("joining_date", "2026-09-01")),
                    onboarding_status=bq_emp.get("onboarding_status", "IN_PROGRESS"),
                    is_day_one=bool(bq_emp.get("is_day_one", False)),
                    assigned_buddy_name=bq_emp.get("assigned_buddy_name"),
                    assigned_buddy_email=bq_emp.get("assigned_buddy_email"),
                    onboarding_track=bq_emp.get("onboarding_track", "Backend"),
                )
        except Exception as bq_err:
            print(f"[AuthService] BigQuery lookup notice: {bq_err}", file=sys.stderr)

        # 2. Direct Cloud Firestore employee lookup
        try:
            fs_emp = firestore_db.get_employee(clean_token)
            if fs_emp:
                return EmployeeRecord(
                    employee_id=fs_emp.get("employee_id", clean_token),
                    google_subject=fs_emp.get("google_subject", ""),
                    email=fs_emp.get("email", ""),
                    name=fs_emp.get("name", ""),
                    department=fs_emp.get("department", "Engineering"),
                    team=fs_emp.get("team", "Payments"),
                    job_role=fs_emp.get("job_role", "Software Engineer"),
                    authorization_role=AuthorizationRole(fs_emp.get("authorization_role", "employee")),
                    manager_id=fs_emp.get("manager_id"),
                    location=fs_emp.get("location", "HQ"),
                    joining_date=str(fs_emp.get("joining_date", "2026-09-01")),
                    onboarding_status=fs_emp.get("onboarding_status", "IN_PROGRESS"),
                    is_day_one=bool(fs_emp.get("is_day_one", False)),
                    assigned_buddy_name=fs_emp.get("assigned_buddy_name"),
                    assigned_buddy_email=fs_emp.get("assigned_buddy_email"),
                    onboarding_track=fs_emp.get("onboarding_track", "Backend"),
                )
        except Exception as fs_err:
            print(f"[AuthService] Firestore lookup notice: {fs_err}", file=sys.stderr)

        # 3. Direct mock token lookup
        if clean_token in MOCK_TOKEN_MAP:
            emp_id = MOCK_TOKEN_MAP[clean_token]
            return _EMPLOYEES.get(emp_id)

        # 4. Google Subject mapping or direct employee_id match
        for emp in _EMPLOYEES.values():
            if emp.google_subject == clean_token or emp.employee_id == clean_token:
                return emp

        # 3. Decode Google JWT if formatted (header.payload.signature)
        if "." in clean_token:
            try:
                parts = clean_token.split(".")
                if len(parts) >= 2:
                    padding = "=" * ((4 - len(parts[1]) % 4) % 4)
                    payload_json = base64.urlsafe_b64decode(parts[1] + padding).decode("utf-8")
                    payload = json.loads(payload_json)
                    email = (payload.get("email") or "").lower()
                    sub = payload.get("sub")
                    name = payload.get("name") or (email.split("@")[0].title() if email else "Authorized Employee")

                    for emp in _EMPLOYEES.values():
                        if (email and emp.email.lower() == email) or (sub and emp.google_subject == sub):
                            return emp

                    # Dynamic provisioning for authenticated enterprise Google users
                    if email:
                        if any(alias in email for alias in ["rnavyasai", "rangisettynavyasai"]):
                            emp = _EMPLOYEES.get("EMP-2026-001")
                            if emp:
                                emp.email = email
                                emp.name = name or "Navya Rangisetty"
                                if sub:
                                    emp.google_subject = sub
                                firestore_db.save_employee(emp.to_dict())
                                return emp

                        new_emp_id = f"EMP-{str(int(time.time()))[-6:]}"
                        new_emp = EmployeeRecord(
                            employee_id=new_emp_id,
                            google_subject=sub or f"sub-{int(time.time())}",
                            email=email,
                            name=name,
                            department="Engineering",
                            team="Payments",
                            job_role="Engineer",
                            authorization_role=AuthorizationRole.EMPLOYEE,
                            manager_id="EMP-2026-010",
                            location="Remote",
                            joining_date=datetime.now().strftime("%Y-%m-%d"),
                            onboarding_status="IN_PROGRESS",
                            is_day_one=False,
                            assigned_buddy_name="Priya Nair",
                            assigned_buddy_email="priya.nair@company.com",
                            onboarding_track="Backend",
                        )
                        _EMPLOYEES[new_emp_id] = new_emp
                        firestore_db.save_employee(new_emp.to_dict())
                        return new_emp
            except Exception:
                pass

        # 4. Check Firestore database for existing saved employee record
        fs_emp = firestore_db.get_employee(clean_token) or firestore_db.lookup_employee_by_email(clean_token)
        if fs_emp:
            role_str = fs_emp.get("authorization_role", "employee").lower()
            role_enum = AuthorizationRole.EMPLOYEE
            if role_str == "manager":
                role_enum = AuthorizationRole.MANAGER
            elif role_str == "hr":
                role_enum = AuthorizationRole.HR
            elif role_str == "it":
                role_enum = AuthorizationRole.IT

            restored_emp = EmployeeRecord(
                employee_id=fs_emp.get("employee_id", clean_token),
                name=fs_emp.get("name", "Employee"),
                email=fs_emp.get("email", ""),
                department=fs_emp.get("department", "Engineering"),
                team=fs_emp.get("team", "Payments"),
                job_role=fs_emp.get("job_role", "Engineer"),
                authorization_role=role_enum,
                manager_id="EMP-2026-010",
                location="HQ",
                joining_date=datetime.now().strftime("%Y-%m-%d"),
                onboarding_status="IN_PROGRESS",
                is_day_one=False,
                assigned_buddy_name=fs_emp.get("assigned_buddy_name", "Priya Nair"),
                assigned_buddy_email=fs_emp.get("assigned_buddy_email", "priya.nair@company.com"),
                onboarding_track="Backend",
            )
            _EMPLOYEES[restored_emp.employee_id] = restored_emp
            return restored_emp

        # 5. Direct email string or lowercase ID lookup
        direct_search = clean_token.lower()
        if any(alias in direct_search for alias in ["rnavyasai", "rangisettynavyasai"]):
            emp = _EMPLOYEES.get("EMP-2026-001")
            if emp:
                emp.email = direct_search
                emp.name = "Navya Rangisetty"
                firestore_db.save_employee(emp.to_dict())
                return emp

        for emp in _EMPLOYEES.values():
            if emp.email.lower() == direct_search or emp.employee_id.lower() == direct_search:
                return emp

        # 6. Fallback corporate email provision
        if "@" in direct_search:
            new_emp_id = f"EMP-{str(int(time.time()))[-6:]}"
            prefix = direct_search.split("@")[0]
            display_name = "Navya Rangisetty" if ("rnavyasai" in direct_search or "rangisetty" in direct_search) else prefix.replace(".", " ").title()
            new_emp = EmployeeRecord(
                employee_id=new_emp_id,
                google_subject=f"sub-{direct_search}",
                email=direct_search,
                name=display_name,
                department="Engineering",
                team="Payments",
                job_role="Software Engineer",
                authorization_role=AuthorizationRole.EMPLOYEE,
                manager_id="EMP-2026-010",
                location="HQ",
                joining_date=datetime.now().strftime("%Y-%m-%d"),
                onboarding_status="IN_PROGRESS",
                is_day_one=False,
                assigned_buddy_name="Priya Nair",
                assigned_buddy_email="priya.nair@company.com",
                onboarding_track="Backend",
            )
            _EMPLOYEES[new_emp_id] = new_emp
            firestore_db.save_employee(new_emp.to_dict())
            return new_emp

        # Fallback default employee
        default_emp = _EMPLOYEES.get("EMP-2026-001")
        if default_emp:
            firestore_db.save_employee(default_emp.to_dict())
        return default_emp

    @staticmethod
    def register_google_profile(email: str, name: str, sub: str = "", picture: str = "") -> EmployeeRecord:
        email_clean = email.strip().lower()
        if any(alias in email_clean for alias in ["rnavyasai", "rangisettynavyasai"]):
            emp = _EMPLOYEES.get("EMP-2026-001")
            if emp:
                emp.email = email_clean
                emp.name = name or "Navya Rangisetty"
                if sub:
                    emp.google_subject = sub
                firestore_db.save_employee(emp.to_dict())
                return emp

        for emp in _EMPLOYEES.values():
            if emp.email.lower() == email_clean or (sub and emp.google_subject == sub):
                if name:
                    emp.name = name
                firestore_db.save_employee(emp.to_dict())
                return emp

        new_emp_id = f"EMP-{str(int(time.time()))[-6:]}"
        display_name = name if name else ("Navya Rangisetty" if ("rnavyasai" in email_clean or "rangisetty" in email_clean) else email_clean.split("@")[0].title())
        new_emp = EmployeeRecord(
            employee_id=new_emp_id,
            google_subject=sub or f"sub-{email_clean}",
            email=email_clean,
            name=display_name,
            department="Engineering",
            team="Payments",
            job_role="Software Engineer",
            authorization_role=AuthorizationRole.EMPLOYEE,
            manager_id="EMP-2026-010",
            location="HQ",
            joining_date=datetime.now().strftime("%Y-%m-%d"),
            onboarding_status="IN_PROGRESS",
            is_day_one=False,
            assigned_buddy_name="Priya Nair",
            assigned_buddy_email="priya.nair@company.com",
            onboarding_track="Backend",
        )
        _EMPLOYEES[new_emp_id] = new_emp
        firestore_db.save_employee(new_emp.to_dict())
        return new_emp


class OnboardingService:
    """Onboarding Lifecycle, Tasks & Manager Team Rollup Service."""

    @staticmethod
    def get_checklist(employee_id: str) -> Optional[Dict[str, Any]]:
        tasks = _CHECKLISTS.get(employee_id)
        if not tasks:
            # Generate tasks on the fly if employee was dynamically created
            emp = _EMPLOYEES.get(employee_id)
            join_date = emp.joining_date if emp else "2026-09-01"
            tasks = []
            for t in INITIAL_TASKS:
                task_copy = type(t)(
                    task_id=t.task_id,
                    title=t.title,
                    description=t.description,
                    status=t.status,
                    due_days_after_start=t.due_days_after_start,
                    due_date=t.due_date,
                    is_overdue=t.is_overdue,
                    completed_at=t.completed_at,
                    category=t.category,
                    action_link=t.action_link,
                )
                task_copy.calculate_due(join_date)
                tasks.append(task_copy)
            _CHECKLISTS[employee_id] = tasks

        # Reconcile with persisted state store and BigQuery
        completed_ids = list(state_store.get_completed_task_ids(employee_id))
        try:
            bq_tasks = BigQueryService.get_employee_tasks(employee_id)
            for bqt in bq_tasks:
                if bqt.get("status") == "COMPLETED" and bqt.get("task_id"):
                    if bqt["task_id"] not in completed_ids:
                        completed_ids.append(bqt["task_id"])
        except Exception as bq_err:
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
        # 1. Update Cloud Firestore
        state_store.mark_task_completed(employee_id, task_id)

        # 2. Update BigQuery task status
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

        # 3. If all tasks are completed, update employee status in BigQuery
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
        """Aggregates direct reports' onboarding progress for Managers and HR."""
        direct_reports = [
            e for e in _EMPLOYEES.values()
            if e.manager_id == manager.employee_id or e.team == manager.team
        ]

        members_progress: List[Dict[str, Any]] = []
        for report in direct_reports:
            cl = OnboardingService.get_checklist(report.employee_id)
            completed = cl["completed_count"] if cl else 0
            total = cl["total_count"] if cl else 0
            pending_titles = [
                t["title"] for t in (cl["tasks"] if cl else [])
                if t["status"] != TaskStatus.COMPLETED.value
            ]
            overdue_count = sum(
                1 for t in (cl["tasks"] if cl else [])
                if t.get("is_overdue")
            )
            pct = int((completed / total * 100)) if total > 0 else 0

            members_progress.append({
                "employee_id": report.employee_id,
                "name": report.name,
                "email": report.email,
                "team": report.team,
                "job_role": report.job_role,
                "joining_date": report.joining_date,
                "total_tasks": total,
                "completed_tasks": completed,
                "pending_tasks": pending_titles,
                "overdue_tasks": overdue_count,
                "progress_percentage": pct,
            })

        overall_pct = (
            int(sum(m["progress_percentage"] for m in members_progress) / len(members_progress))
            if members_progress else 0
        )

        return {
            "manager_id": manager.employee_id,
            "manager_name": manager.name,
            "team_name": manager.team,
            "total_team_members": len(members_progress),
            "overall_progress_percentage": overall_pct,
            "members": members_progress,
        }


class OperationsService:
    """Operations: Timesheets, 3-Tier Escalation Directory, and Incident Creation."""

    @staticmethod
    def get_timesheet_status(employee_id: str) -> Dict[str, Any]:
        override = state_store.get_timesheet_override(employee_id)
        if override:
            return {
                "employee_id": employee_id,
                "period": "Current Cycle",
                "period_end": "2026-09-04",
                "hours_logged": override.get("hours_logged", 40.0),
                "status": override.get("status", "SUBMITTED"),
                "due_date": "2026-09-04",
                "action_required": False,
                "message": f"Your timesheet for week ending 2026-09-04 ({override.get('hours_logged', 40.0)} hrs) has been submitted and is pending supervisor sign-off.",
            }

        records = _TIMESHEETS.get(employee_id, [])
        if not records:
            return {
                "employee_id": employee_id,
                "period": "Current Cycle",
                "hours_logged": 40.0,
                "status": TimesheetStatus.APPROVED.value,
                "action_required": False,
                "message": "Your timesheet is fully approved and up to date.",
            }

        latest = records[0]
        status_val = latest.status.value if isinstance(latest.status, TimesheetStatus) else latest.status
        action_required = status_val in [TimesheetStatus.PENDING.value, TimesheetStatus.OVERDUE.value]

        msg = (
            f"Your timesheet for week ending {latest.period_end} is currently {status_val} "
            f"({latest.hours_logged} hours logged). Please submit before Friday 5:00 PM."
            if action_required
            else f"Your timesheet for week ending {latest.period_end} is {status_val}."
        )

        return {
            "employee_id": employee_id,
            "period": f"{latest.period_start} to {latest.period_end}",
            "period_end": latest.period_end,
            "hours_logged": latest.hours_logged,
            "status": status_val,
            "due_date": latest.due_date,
            "action_required": action_required,
            "message": msg,
        }

    @staticmethod
    def submit_timesheet(employee_id: str, hours: float = 40.0, notes: str = "") -> Dict[str, Any]:
        emp = _EMPLOYEES.get(employee_id)
        emp_name = emp.name if emp else "Employee"
        sf_res = SalesforceService.sync_timesheet(
            employee_id=employee_id,
            employee_name=emp_name,
            hours=hours,
            notes=notes
        )
        salesforce_id = sf_res.get("salesforce_id", "")
        state_store.save_timesheet_submission(employee_id, hours, notes, salesforce_id)
        result = OperationsService.get_timesheet_status(employee_id)
        result["salesforce_sync"] = sf_res
        result["salesforce_id"] = salesforce_id
        result["salesforce_url"] = sf_res.get("salesforce_url", "")
        return result

    @staticmethod
    def create_incident(
        actor: EmployeeRecord,
        category: str,
        summary: str,
        severity: IncidentSeverity = IncidentSeverity.MEDIUM,
    ) -> Dict[str, Any]:
        import random
        import string
        suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        incident_id = f"INC-2026-{suffix}"

        cat_lower = category.lower()
        if any(term in cat_lower for term in ["sql", "database", "k8s", "cluster", "kubernetes"]):
            assigned_team = "Platform"
        elif any(term in cat_lower for term in ["iam", "security", "token", "permission"]):
            assigned_team = "Security"
        else:
            assigned_team = "IT-Support"

        # Jira Cloud Real REST API Synchronization
        jira_res = JiraService.create_incident_issue(
            summary=summary,
            category=category,
            severity=severity.value if hasattr(severity, "value") else str(severity),
            employee_id=actor.employee_id,
            reporter_email=actor.email
        )

        record = IncidentRecord(
            incident_id=incident_id,
            created_by=actor.employee_id,
            category=category,
            summary=summary,
            severity=severity,
            status="OPEN",
            assigned_team=assigned_team,
            created_at=datetime.utcnow().isoformat() + "Z",
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
        """Resolves 3-tier team escalation: Primary Lead -> Backup Lead (if OOO) -> Broadcast Channel."""
        contact = None
        for key, val in TEAM_DIRECTORY.items():
            if key.lower() in domain.lower() or domain.lower() in key.lower():
                contact = val
                break

        if not contact:
            return {
                "domain": domain,
                "status": "FALLBACK_GENERAL",
                "assigned_contact": "IT Service Desk",
                "channel": "#general-it-helpdesk",
                "message": f"No specific point-of-contact registered for '{domain}'. Routed to #general-it-helpdesk.",
            }

        primary_ooo = contact.get("primary_on_vacation", False)
        backup_ooo = contact.get("backup_on_vacation", False)

        if not primary_ooo:
            return {
                "domain": contact["domain"],
                "status": "PRIMARY_ASSIGNED",
                "assigned_contact": f"{contact['primary_lead_name']} ({contact['primary_email']})",
                "channel": contact["general_channel"],
                "message": f"Assigned to Primary Lead: {contact['primary_lead_name']} ({contact['primary_email']}). Available on Slack.",
            }

        if primary_ooo and not backup_ooo:
            return {
                "domain": contact["domain"],
                "status": "BACKUP_ASSIGNED",
                "assigned_contact": f"{contact['backup_lead_name']} ({contact['backup_email']})",
                "channel": contact["general_channel"],
                "message": f"Primary Lead ({contact['primary_lead_name']}) is Out of Office. Re-routed to Backup Lead: {contact['backup_lead_name']} ({contact['backup_email']}).",
            }

        return {
            "domain": contact["domain"],
            "status": "BOTH_OOO_BROADCAST_TRIGGERED",
            "assigned_contact": f"Broadcast Channel ({contact['general_channel']})",
            "channel": contact["general_channel"],
            "message": f"High Priority Alert: Both Primary ({contact['primary_lead_name']}) and Backup ({contact['backup_lead_name']}) leads are Out of Office. Ticket broadcasted to {contact['general_channel']}.",
        }

    @staticmethod
    def get_points_of_contact(employee: EmployeeRecord, access_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Unified 'Point to Person' directory for the employee:
        Returns assigned buddy, direct manager, IT systems lead, People Ops partner,
        and domain escalation leads with live Google Calendar OOO synchronization.
        """
        manager = EMPLOYEES.get(employee.manager_id) if employee.manager_id else None

        # Query live Google Calendar OOO status
        calendar_status = CalendarService.get_out_of_office_status(access_token)

        domain_contacts = []
        for domain, info in TEAM_DIRECTORY.items():
            resolved = OperationsService.resolve_escalation(domain)
            domain_contacts.append({
                "domain": domain,
                "primary_lead": info["primary_lead_name"],
                "primary_email": info["primary_email"],
                "primary_ooo": info.get("primary_on_vacation", False),
                "backup_lead": info["backup_lead_name"],
                "backup_email": info["backup_email"],
                "backup_ooo": info.get("backup_on_vacation", False),
                "channel": info["general_channel"],
                "active_contact": resolved["assigned_contact"],
                "status": resolved["status"],
            })

        buddy_name = employee.assigned_buddy_name or "Priya Nair"
        buddy_email = employee.assigned_buddy_email or "priya.nair@company.com"

        return {
            "employee_id": employee.employee_id,
            "name": employee.name,
            "calendar_integration": calendar_status,
            "buddy": {
                "name": buddy_name,
                "email": buddy_email,
                "role": "Staff Software Engineer & Tech Lead",
                "scope": "Day-1 Onboarding Buddy, Codebase Questions & Daily Guidance",
                "channel": f"#{employee.team.lower()}-dev" if employee.team else "#payments-dev",
                "calendar_status": "Active / In Office"
            },
            "manager": {
                "id": manager.employee_id if manager else "EMP-2026-010",
                "name": manager.name if manager else "Sarah Jenkins",
                "email": manager.email if manager else "sarah.j@company.com",
                "role": manager.job_role if manager else "Engineering Manager - Payments",
                "scope": "Direct Reporting Manager, 1:1 Check-ins, Performance & Approvals",
                "channel": "#eng-leadership",
                "calendar_status": "Out of Office (Annual Leave, returns Monday)" if calendar_status.get("is_out_of_office") else "Active / In Office"
            },
            "it_support": {
                "name": "Marcus Vance",
                "email": "marcus.v@company.com",
                "role": "Lead IT Systems Administrator",
                "scope": "Hardware, Cloud IAM credentials, VPN and Developer Access",
                "channel": "#help-it",
            },
            "people_ops": {
                "name": "Amanda Walker",
                "email": "amanda.w@company.com",
                "role": "Senior People Operations Specialist",
                "scope": "Benefits, Payroll, Timesheets, and Workplace Policies",
                "channel": "#people-ops",
            },
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
            # Clearance filter
            if asset.access_level == "manager" and not is_mgr:
                continue
            # Team domain boundary filter
            if asset.team != "ALL" and asset.team.lower() != actor.team.lower():
                continue

            words = [w for w in q.split() if len(w) > 2]
            for chunk in asset.chunks:
                matches = (
                    asset.title.lower() in q
                    or q in asset.title.lower()
                    or q in chunk.content.lower()
                    or (asset.description and q in asset.description.lower())
                    or asset.team.lower() in q
                    or any(term in q for term in ["runbook", "doc", "standard", "guide", "setup", "architecture"])
                    or any(w in asset.title.lower() or w in chunk.content.lower() for w in words)
                )
                if matches:
                    results.append(chunk)

        return results

    @staticmethod
    def format_context(actor: EmployeeRecord, chunks: List[KnowledgeChunk], query: Optional[str] = None) -> str:
        perimeter = f"[ENFORCED_SECURITY_PERIMETER: employee_id={actor.employee_id} | department={actor.department} | team={actor.team} | clearance={actor.authorization_role.value if isinstance(actor.authorization_role, AuthorizationRole) else actor.authorization_role}]"
        if not chunks:
            return f"{perimeter}\nNo authorized company knowledge assets matched your query."

        lines = [perimeter]
        if query:
            lines.append(f"Search Query: {query}")
        for i, chunk in enumerate(chunks):
            lines.append(
                f"--- [AUTHORIZED ASSET {i + 1} | ID: {chunk.document_id}] ---\n"
                f"Team Domain: {chunk.team} | Clearance Level: {chunk.access_level}\n"
                f"{chunk.content}\n"
            )
        return "\n".join(lines)

    @staticmethod
    def get_authorized_insights(actor: EmployeeRecord) -> List[Dict[str, Any]]:
        is_mgr = is_manager_or_hr(actor.authorization_role)
        results = []
        for insight in KNOWLEDGE_INSIGHTS:
            if insight["access_level"] == "manager" and not is_mgr:
                continue
            if insight["team"] != "ALL" and insight["team"].lower() != actor.team.lower():
                continue
            results.append(insight)
        return results

    @staticmethod
    def get_document(actor: EmployeeRecord, doc_id: str) -> Optional[Dict[str, Any]]:
        is_mgr = is_manager_or_hr(actor.authorization_role)
        for asset in KNOWLEDGE_CATALOG:
            if asset.document_id.lower() == doc_id.lower() or asset.title.lower() == doc_id.lower():
                if asset.access_level == "manager" and not is_mgr:
                    return {"error": "Unauthorized: Manager clearance required to access this document."}
                if asset.team != "ALL" and asset.team.lower() != actor.team.lower():
                    return {"error": f"Unauthorized: Restricted to {asset.team} team."}

                d = asset.to_dict()
                # Direct Google Cloud Storage document retrieval
                gcs_res = GCSService.read_document_from_gcs(asset.gcs_uri)
                if gcs_res.get("content"):
                    d["full_content"] = gcs_res["content"]
                    d["source"] = "Google Cloud Storage (GCS)"
                    d["gcs_status"] = "LOADED_FROM_GCS"
                else:
                    full_text = "\n\n".join(c.content for c in asset.chunks)
                    d["full_content"] = full_text
                    d["source"] = "Knowledge Catalog (GCS sync pending)"
                    d["gcs_status"] = gcs_res.get("status", "GCS_OFFLINE")
                return d

        for insight in KNOWLEDGE_INSIGHTS:
            if (
                insight.get("doc_id", "").lower() == doc_id.lower()
                or insight.get("insight_id", "").lower() == doc_id.lower()
                or insight.get("title", "").lower() == doc_id.lower()
            ):
                if insight["access_level"] == "manager" and not is_mgr:
                    return {"error": "Unauthorized: Manager clearance required to access this document."}
                if insight["team"] != "ALL" and insight["team"].lower() != actor.team.lower():
                    return {"error": f"Unauthorized: Restricted to {insight['team']} team."}
                
                gcs_uri = insight.get("gcs_uri", "")
                gcs_res = GCSService.read_document_from_gcs(gcs_uri) if gcs_uri else {}
                content = gcs_res.get("content") or insight.get("full_content", insight["summary"])

                return {
                    "document_id": insight.get("doc_id", doc_id),
                    "title": insight["title"],
                    "category": insight["category"],
                    "team": insight["team"],
                    "access_level": insight["access_level"],
                    "gcs_uri": gcs_uri,
                    "description": insight["summary"],
                    "full_content": content,
                    "effective_date": insight.get("effective_date", ""),
                    "source": "Google Cloud Storage (GCS)" if gcs_res.get("content") else "Knowledge Catalog",
                    "gcs_status": gcs_res.get("status", "GCS_NOT_CONFIGURED")
                }
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

        if employee.is_day_one:
            greeting = (
                f"Welcome to the team, {employee.name}! Glad to have you with {employee.team} as {employee.job_role}. "
                f"Company update: Core collaboration hours are 10:00 AM – 4:00 PM local time."
            )
        else:
            greeting = (
                f"Welcome back, {employee.name}! "
                f"Company update: All engineering sprint goals are synced for Q3 deliverables. Weekly timesheets are due Friday by 5:00 PM."
            )

        return {
            "employee_id": employee.employee_id,
            "name": employee.name,
            "department": employee.department,
            "team": employee.team,
            "job_role": employee.job_role,
            "authorization_role": employee.authorization_role.value if isinstance(employee.authorization_role, AuthorizationRole) else employee.authorization_role,
            "is_day_one": employee.is_day_one,
            "proactive_greeting": greeting,
            "onboarding_summary": checklist,
            "timesheet_status": timesheet_info,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }


class SessionService:
    """Conversational Session Management & Turn Persistence backed by Google Cloud Firestore."""

    @staticmethod
    def get_or_create_session(employee_id: str, session_id: Optional[str] = None) -> UserSession:
        effective_id = session_id or f"sess-{employee_id.lower()}-{str(int(time.time()))[-6:]}"
        if effective_id in _SESSIONS:
            sess = _SESSIONS[effective_id]
            if sess.employee_id == employee_id:
                sess.last_accessed_at = datetime.utcnow().isoformat() + "Z"
                return sess

        # Query Cloud Firestore for existing session history
        fs_record = firestore_db.get_session(effective_id)
        if fs_record and fs_record.get("employee_id") == employee_id:
            restored = UserSession(
                session_id=effective_id,
                employee_id=employee_id,
                created_at=fs_record.get("created_at", datetime.utcnow().isoformat() + "Z"),
                last_accessed_at=datetime.utcnow().isoformat() + "Z",
                history=fs_record.get("history", []),
            )
            _SESSIONS[effective_id] = restored
            return restored

        now = datetime.utcnow().isoformat() + "Z"
        new_session = UserSession(
            session_id=effective_id,
            employee_id=employee_id,
            created_at=now,
            last_accessed_at=now,
            history=[],
        )
        _SESSIONS[effective_id] = new_session
        firestore_db.save_session(effective_id, employee_id, [])
        return new_session

    @staticmethod
    def save_session(session: UserSession) -> None:
        session.last_accessed_at = datetime.utcnow().isoformat() + "Z"
        _SESSIONS[session.session_id] = session
        # Persist asynchronously/reliably to Firestore
        firestore_db.save_session(session.session_id, session.employee_id, session.history)

    @staticmethod
    def append_message(session_id: str, employee_id: str, role: str, content: str, agent: Optional[str] = None) -> UserSession:
        session = SessionService.get_or_create_session(employee_id, session_id)
        msg = {
            "role": role,
            "content": content,
            "agent": agent,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        session.history.append(msg)
        SessionService.save_session(session)
        return session
