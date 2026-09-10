#!/usr/bin/env python3
"""
Company AI Assistant: Master Database-Driven Data Access Layer
Directly queries and mutates Google Cloud BigQuery tables:
  - patchamomma-505416.employee_ai.employees
  - patchamomma-505416.employee_ai.employee_onboarding_tasks
  - patchamomma-505416.employee_ai.knowledge_assets
  - patchamomma-505416.employee_ai.knowledge_chunks
  - patchamomma-505416.employee_ai.timesheets
  - patchamomma-505416.employee_ai.incidents
  - patchamomma-505416.employee_ai.team_directory_mesh
All data comes directly from the cloud database. No local SQLite or enterprise.db.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from backend.bigquery_service import BigQueryService
from backend.models import (
    EmployeeRecord, AuthorizationRole, OnboardingTask, TaskStatus,
    KnowledgeAsset, KnowledgeChunk, TimesheetRecord, TimesheetStatus,
    IncidentRecord, IncidentSeverity
)

def row_to_employee(r: Dict[str, Any]) -> EmployeeRecord:
    role_str = str(r.get('authorization_role', 'employee')).lower()
    try:
        auth_role = AuthorizationRole(role_str)
    except ValueError:
        auth_role = AuthorizationRole.EMPLOYEE
    return EmployeeRecord(
        employee_id=str(r.get('employee_id', '')),
        google_subject=str(r.get('google_subject', '')),
        email=str(r.get('email', '')),
        name=str(r.get('name', '')),
        department=str(r.get('department', 'Engineering')),
        team=str(r.get('team', 'Unassigned')),
        job_role=str(r.get('job_role', 'Software Engineer')),
        authorization_role=auth_role,
        manager_id=r.get('manager_id'),
        location=str(r.get('location', 'HQ')),
        joining_date=str(r.get('joining_date', datetime.utcnow().strftime("%Y-%m-%d"))),
        onboarding_status=str(r.get('onboarding_status', 'NOT_STARTED')),
        is_day_one=bool(r.get('is_day_one', True)),
        assigned_buddy_name=r.get('assigned_buddy_name'),
        assigned_buddy_email=r.get('assigned_buddy_email'),
        onboarding_track=str(r.get('onboarding_track', 'General')),
    )

def get_all_employees() -> Dict[str, EmployeeRecord]:
    rows = BigQueryService.get_all_employees()
    result = {}
    for r in rows:
        emp = row_to_employee(r)
        if emp.employee_id:
            result[emp.employee_id] = emp
    return result

class DynamicEmployees(dict):
    """Dynamic dictionary backed directly by BigQuery table employees."""
    def __getitem__(self, key):
        emp_data = BigQueryService.get_employee(str(key))
        if emp_data and isinstance(emp_data, list) and len(emp_data) > 0:
            return row_to_employee(emp_data[0])
        elif isinstance(emp_data, dict):
            return row_to_employee(emp_data)
        raise KeyError(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except (KeyError, Exception):
            return default

    def values(self):
        return get_all_employees().values()

    def items(self):
        return get_all_employees().items()

    def keys(self):
        return get_all_employees().keys()

    def __len__(self):
        return len(get_all_employees())

    def __iter__(self):
        return iter(get_all_employees())

    def __contains__(self, key):
        emp = self.get(key)
        return emp is not None

    def __setitem__(self, key, emp):
        role_val = emp.authorization_role.value if hasattr(emp.authorization_role, 'value') else str(emp.authorization_role)
        project = BigQueryService.get_project_id()
        dataset = BigQueryService.get_dataset()
        mgr = f"'{emp.manager_id}'" if emp.manager_id else "NULL"
        sql = (
            f"INSERT INTO `{project}.{dataset}.employees` "
            f"(employee_id, google_subject, email, name, department, team, job_role, authorization_role, manager_id, location, joining_date, onboarding_status, is_day_one, assigned_buddy_name, assigned_buddy_email, onboarding_track) "
            f"VALUES ('{emp.employee_id}', '{emp.google_subject}', '{emp.email}', '{emp.name}', '{emp.department}', '{emp.team}', '{emp.job_role}', '{role_val}', "
            f"{mgr}, '{emp.location}', DATE('{emp.joining_date}'), '{emp.onboarding_status}', {str(emp.is_day_one).upper()}, '{emp.assigned_buddy_name or ''}', '{emp.assigned_buddy_email or ''}', '{emp.onboarding_track}')"
        )
        BigQueryService.execute_query(sql)

EMPLOYEES = DynamicEmployees()

class DynamicTasks(dict):
    """Dynamic task dictionary backed directly by BigQuery table employee_onboarding_tasks."""
    def __getitem__(self, emp_id):
        rows = BigQueryService.get_employee_tasks(str(emp_id))
        tasks = []
        for r in rows:
            stat_str = str(r.get('status', 'PENDING')).upper()
            try:
                task_stat = TaskStatus(stat_str)
            except ValueError:
                task_stat = TaskStatus.PENDING
            tasks.append(
                OnboardingTask(
                    task_id=str(r.get('task_id', '')),
                    title=str(r.get('title', '')),
                    description=str(r.get('description', '')),
                    status=task_stat,
                    due_days_after_start=int(r.get('due_days_after_start', 1) or 1),
                    completed_at=str(r.get('completed_at', '')) if r.get('completed_at') else None,
                    category=str(r.get('category', 'General')),
                    action_link=r.get('action_link')
                )
            )
        return tasks

    def get(self, emp_id, default=None):
        try:
            res = self[emp_id]
            return res if res else (default if default is not None else [])
        except Exception:
            return default if default is not None else []

ONBOARDING_TASKS = DynamicTasks()

class DynamicTimesheets(dict):
    """Dynamic timesheets dictionary backed directly by BigQuery table timesheets."""
    def __getitem__(self, emp_id):
        rows = BigQueryService.get_timesheet_status(str(emp_id))
        sheets = []
        for r in rows:
            stat_str = str(r.get('status', 'PENDING')).upper()
            try:
                ts_stat = TimesheetStatus(stat_str)
            except ValueError:
                ts_stat = TimesheetStatus.PENDING
            sheets.append(
                TimesheetRecord(
                    timesheet_id=str(r.get('timesheet_id', '')),
                    employee_id=str(r.get('employee_id', emp_id)),
                    period_start=str(r.get('period_start', '')),
                    period_end=str(r.get('period_end', '')),
                    hours_logged=float(r.get('hours_logged', 40.0) or 40.0),
                    status=ts_stat,
                    due_date=str(r.get('due_date', ''))
                )
            )
        return sheets

    def get(self, emp_id, default=None):
        try:
            res = self[emp_id]
            return res if res else (default if default is not None else [])
        except Exception:
            return default if default is not None else []

    def items(self):
        project = BigQueryService.get_project_id()
        dataset = BigQueryService.get_dataset()
        res = BigQueryService.execute_query(f"SELECT DISTINCT employee_id FROM `{project}.{dataset}.timesheets`")
        emp_ids = [r['employee_id'] for r in res.get('rows', [])]
        return [(eid, self[eid]) for eid in emp_ids]

TIMESHEETS = DynamicTimesheets()

def get_all_incidents() -> List[IncidentRecord]:
    rows = BigQueryService.get_incidents()
    incidents = []
    for r in rows:
        sev_str = str(r.get('severity', 'MEDIUM')).upper()
        try:
            sev = IncidentSeverity(sev_str)
        except ValueError:
            sev = IncidentSeverity.MEDIUM
        incidents.append(
            IncidentRecord(
                incident_id=str(r.get('incident_id', '')),
                created_by=str(r.get('created_by', '')),
                category=str(r.get('category', 'IT')),
                summary=str(r.get('summary', '')),
                severity=sev,
                status=str(r.get('status', 'OPEN')),
                assigned_team=str(r.get('assigned_team', 'IT-Support')),
                created_at=str(r.get('created_at', '')),
                jira_key=r.get('jira_key'),
                jira_url=r.get('jira_url')
            )
        )
    return incidents

class DynamicIncidents(list):
    """Dynamic incident list backed directly by BigQuery table incidents."""
    def __iter__(self):
        return iter(get_all_incidents())
    def __len__(self):
        return len(get_all_incidents())
    def append(self, inc):
        sev_val = inc.severity.value if hasattr(inc.severity, 'value') else str(inc.severity)
        BigQueryService.create_incident({
            "incident_id": inc.incident_id,
            "created_by": inc.created_by,
            "category": inc.category,
            "summary": inc.summary,
            "severity": sev_val,
            "status": inc.status,
            "assigned_team": inc.assigned_team,
            "created_at": inc.created_at
        })

INCIDENTS = DynamicIncidents()

def get_all_team_directory() -> Dict[str, Dict[str, Any]]:
    rows = BigQueryService.get_team_escalation()
    directory: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        domain = r.get('system_domain', '')
        if domain:
            directory[domain] = {
                'domain': domain,
                'primary_lead_name': r.get('primary_lead_name', ''),
                'primary_email': r.get('primary_email', ''),
                'primary_on_vacation': bool(r.get('primary_on_vacation', False)),
                'backup_lead_name': r.get('backup_lead_name', ''),
                'backup_email': r.get('backup_email', ''),
                'backup_on_vacation': bool(r.get('backup_on_vacation', False)),
                'general_channel': r.get('general_team_channel', '#general-support'),
                'general_team_channel': r.get('general_team_channel', '#general-support'),
            }
    return directory

TEAM_DIRECTORY = get_all_team_directory()

def get_all_knowledge_catalog() -> List[KnowledgeAsset]:
    project = BigQueryService.get_project_id()
    dataset = BigQueryService.get_dataset()
    assets_res = BigQueryService.execute_query(f"SELECT * FROM `{project}.{dataset}.knowledge_assets` ORDER BY document_id ASC")
    chunks_res = BigQueryService.execute_query(f"SELECT * FROM `{project}.{dataset}.knowledge_chunks` ORDER BY chunk_index ASC")
    
    chunks_by_doc: Dict[str, List[KnowledgeChunk]] = {}
    for c in chunks_res.get('rows', []):
        doc_id = str(c.get('document_id', ''))
        if doc_id not in chunks_by_doc:
            chunks_by_doc[doc_id] = []
        chunks_by_doc[doc_id].append(
            KnowledgeChunk(
                chunk_id=str(c.get('chunk_id', '')),
                document_id=doc_id,
                content=str(c.get('content', '')),
                access_level=str(c.get('access_level', 'employee')),
                team=str(c.get('team', 'ALL')),
                chunk_index=int(c.get('chunk_index', 0))
            )
        )
        
    result = []
    for a in assets_res.get('rows', []):
        doc_id = str(a.get('document_id', ''))
        result.append(
            KnowledgeAsset(
                document_id=doc_id,
                title=str(a.get('title', '')),
                source=str(a.get('source', '')),
                gcs_uri=str(a.get('gcs_uri', '')),
                team=str(a.get('team', 'ALL')),
                access_level=str(a.get('access_level', 'employee')),
                document_type=str(a.get('document_type', 'Guide')),
                owner=str(a.get('owner', 'Engineering')),
                description=str(a.get('description', '')),
                chunks=chunks_by_doc.get(doc_id, [])
            )
        )
    return result

KNOWLEDGE_CATALOG = get_all_knowledge_catalog()
KNOWLEDGE_INSIGHTS = []
