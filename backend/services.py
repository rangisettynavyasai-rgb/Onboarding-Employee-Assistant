#!/usr/bin/env python3
"""
Company AI Assistant: Enterprise Domain Services (Python)
Unified operation lifecycle service definitions.
"""
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
class AuthService:
    """Enterprise Identity & Token Resolution Service."""

    @staticmethod
    def authenticate_credentials(identity: str, password: Optional[str] = None) -> Optional[EmployeeRecord]:
        emp = AuthService.resolve_employee(identity)
        if not emp:
            return None
        return emp

    @staticmethod
    def resolve_employee(bearer_token_or_id: str) -> Optional[EmployeeRecord]:
        if not bearer_token_or_id:
            return None
        clean_token = bearer_token_or_id.replace("Bearer ", "").strip() if bearer_token_or_id.lower().startswith("bearer ") else bearer_token_or_id.strip()

        # CRITICAL SDK FIX: Extract the dictionary safely from the returned BigQuery Row list
        try:
            bq_res = BigQueryService.get_employee(clean_token)
            if bq_res and isinstance(bq_res, list) and len(bq_res) > 0:
                bq_emp = bq_res[0]
                role_val = bq_emp.get("authorization_role", "employee").lower()
                return EmployeeRecord(
                    employee_id=bq_emp.get("employee_id", clean_token), google_subject=bq_emp.get("google_subject", ""),
                    email=bq_emp.get("email", ""), name=bq_emp.get("name", ""), department=bq_emp.get("department", "Engineering"),
                    team=bq_emp.get("team", "Payments"), job_role=bq_emp.get("job_role", "Software Engineer"),
                    authorization_role=AuthorizationRole(role_val if role_val in ["employee", "manager", "hr", "it"] else "employee"),
                    manager_id=bq_emp.get("manager_id"), location=bq_emp.get("location", "HQ"), joining_date=str(bq_emp.get("joining_date", "2026-09-01")),
                    onboarding_status=bq_emp.get("onboarding_status", "IN_PROGRESS"), is_day_one=bool(bq_emp.get("is_day_one", False)),
                    assigned_buddy_name=bq_emp.get("assigned_buddy_name"), assigned_buddy_email=bq_emp.get("assigned_buddy_email"), onboarding_track=bq_emp.get("onboarding_track", "Backend")
                )
        except Exception as bq_err:
            print(f"[AuthService] BigQuery lookup notice: {bq_err}", file=sys.stderr)

        try:
            fs_emp = firestore_db.get_employee(clean_token)
            if fs_emp:
                role_val = fs_emp.get("authorization_role", "employee").lower()
                return EmployeeRecord(
                    employee_id=fs_emp.get("employee_id", clean_token), google_subject=fs_emp.get("google_subject", ""),
                    email=fs_emp.get("email", ""), name=fs_emp.get("name", ""), department=fs_emp.get("department", "Engineering"),
                    team=fs_emp.get("team", "Payments"), job_role=fs_emp.get("job_role", "Software Engineer"),
                    authorization_role=AuthorizationRole(role_val if role_val in ["employee", "manager", "hr", "it"] else "employee"),
                    manager_id=fs_emp.get("manager_id"), location=fs_emp.get("location", "HQ"), joining_date=str(fs_emp.get("joining_date", "2026-09-01")),
                    onboarding_status=fs_emp.get("onboarding_status", "IN_PROGRESS"), is_day_one=bool(fs_emp.get("is_day_one", False)),
                    assigned_buddy_name=fs_emp.get("assigned_buddy_name"), assigned_buddy_email=fs_emp.get("assigned_buddy_email"), onboarding_track=fs_emp.get("onboarding_track", "Backend")
                )
        except Exception as fs_err:
            print(f"[AuthService] Firestore lookup notice: {fs_err}", file=sys.stderr)

        if clean_token in MOCK_TOKEN_MAP:
            return _EMPLOYEES.get(MOCK_TOKEN_MAP[clean_token])

        for emp in _EMPLOYEES.values():
            if emp.google_subject == clean_token or emp.employee_id == clean_token or emp.email.lower() == clean_token.lower():
                return emp
        return None

    @staticmethod
    def register_google_profile(email: str, name: str, sub: str = "") -> EmployeeRecord:
        email_clean = email.strip().lower()

        # CRITICAL SDK FIX: Unpack list safely from official BigQuery Client rows
        try:
            bq_res = BigQueryService.get_employee(email_clean)
            if bq_res and isinstance(bq_res, list) and len(bq_res) > 0:
                bq_emp = bq_res[0]
                role_val = bq_emp.get("authorization_role", "employee").lower()
                emp = EmployeeRecord(
                    employee_id=bq_emp.get("employee_id", "EMP-2026-001"), google_subject=sub or bq_emp.get("google_subject", ""),
                    email=email_clean, name=name or bq_emp.get("name", "Employee"), department=bq_emp.get("department", "Engineering"),
                    team=bq_emp.get("team", "Payments"), job_role=bq_emp.get("job_role", "Software Engineer"),
                    authorization_role=AuthorizationRole(role_val if role_val in ["employee", "manager", "hr", "it"] else "employee"),
                    manager_id=bq_emp.get("manager_id"), location=bq_emp.get("location", "HQ"), joining_date=str(bq_emp.get("joining_date", "2026-09-01")),
                    onboarding_status=bq_emp.get("onboarding_status", "IN_PROGRESS"), is_day_one=bool(bq_emp.get("is_day_one", False)),
                    assigned_buddy_name=bq_emp.get("assigned_buddy_name", "Priya Nair"), assigned_buddy_email=bq_emp.get("assigned_buddy_email", "priya.nair@company.com"), onboarding_track=bq_emp.get("onboarding_track", "Backend")
                )
                _EMPLOYEES[emp.employee_id] = emp
                firestore_db.save_employee(emp.to_dict())
                return emp
        except Exception as bq_err:
            print(f"[AuthService] BigQuery lookup notice in register_google_profile: {bq_err}", file=sys.stderr)

        for emp in _EMPLOYEES.values():
            if emp.email.lower() == email_clean or (sub and emp.google_subject == sub):
                if name: emp.name = name
                firestore_db.save_employee(emp.to_dict())
                return emp

        new_id = f"EMP-{str(int(time.time()))[-6:]}"
        new_emp = EmployeeRecord(
            employee_id=new_id, google_subject=sub or f"sub-{email_clean}", email=email_clean, name=name or email_clean.split("@")[0].title(),
            department="Engineering", team="Payments", job_role="Software Engineer", authorization_role=AuthorizationRole.EMPLOYEE,
            manager_id="EMP-2026-010", location="HQ", joining_date=datetime.now().strftime("%Y-%m-%d"), onboarding_status="IN_PROGRESS",
            is_day_one=False, assigned_buddy_name="Priya Nair", assigned_buddy_email="priya.nair@company.com", onboarding_track="Backend"
        )
        _EMPLOYEES[new_id] = new_emp
        firestore_db.save_employee(new_emp.to_dict())
        return new_emp
class OnboardingService:
    """Onboarding Lifecycle, Tasks & Manager Team Rollup Service."""

    @staticmethod
    def get_checklist(employee_id: str) -> Optional[Dict[str, Any]]:
        tasks = _CHECKLISTS.get(employee_id)
        if not tasks:
            emp = _EMPLOYEES.get(employee_id)
            join_date = emp.joining_date if emp else "2026-09-01"
            tasks = []
            for t in _CHECKLISTS.get("EMP-2026-001", []):
                task_copy = OnboardingTask(
                    task_id=t.task_id, title=t.title, description=t.description, status=t.status,
                    due_days_after_start=t.due_days_after_start, due_date=t.due_date,
                    is_overdue=t.is_overdue, completed_at=t.completed_at, category=t.category, action_link=t.action_link
                )
                task_copy.calculate_due(join_date)
                tasks.append(task_copy)
            _CHECKLISTS[employee_id] = tasks

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
        result = OperationsService.get_timesheet_status(employee_id)
        result["salesforce_sync"] = sf_res
        result["salesforce_id"] = salesforce_id
        result["salesforce_url"] = sf_res.get("salesforce_url", "")
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
        manager = _EMPLOYEES.get(employee.manager_id) if employee.manager_id else None
        calendar_status = CalendarService.get_out_of_office_status(access_token)

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
            "buddy": {
                "name": employee.assigned_buddy_name or "Priya Nair", "email": employee.assigned_buddy_email or "priya.nair@company.com",
                "role": "Staff Software Engineer & Tech Lead", "scope": "Day-1 Guidance & Code walkthroughs", "channel": f"#{employee.team.lower()}-dev" if employee.team else "#payments-dev",
            },
            "manager": {
                "id": manager.employee_id if manager else "EMP-2026-010", "name": manager.name if manager else "Sarah Jenkins", "email": manager.email if manager else "sarah.j@company.com",
                "role": manager.job_role if manager else "Engineering Manager", "scope": "Check-ins & Approvals", "channel": "#eng-leadership",
            },
            "it_support": {"name": "Marcus Vance", "email": "marcus.v@company.com", "role": "Lead IT Admin", "scope": "Hardware & IAM credentials", "channel": "#help-it"},
            "people_ops": {"name": "Amanda Walker", "email": "amanda.w@company.com", "role": "Senior People Ops Specialist", "scope": "Benefits & Workplace Policies", "channel": "#people-ops"},
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
            lines.append(f"--- [AUTHORIZED ASSET {i + 1} | ID: {chunk.document_id}] ---\n{chunk.content}\n")
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
                "insight_id": f"INS-{asset.document_id}",
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
            greeting = f"Welcome to the team, {employee.name}! Glad to have you with {employee.team} as {employee.job_role}."

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
