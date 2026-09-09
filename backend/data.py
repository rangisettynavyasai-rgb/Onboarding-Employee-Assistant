#!/usr/bin/env python3
"""
Company AI Assistant: Master Database-Driven Data Access Layer
All synthetic data is loaded directly from bigquery/tables.sql and bigquery/seed_data.sql
into the enterprise database. No hardcoded in-memory state.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from backend.db import db
from backend.models import (
    EmployeeRecord, AuthorizationRole, OnboardingTask, TaskStatus,
    KnowledgeAsset, KnowledgeChunk, TimesheetRecord, TimesheetStatus,
    IncidentRecord, IncidentSeverity
)

def get_all_employees() -> Dict[str, EmployeeRecord]:
    rows = db.query('SELECT * FROM employees ORDER BY employee_id ASC')
    result = {}
    for r in rows:
        role_str = str(r.get('authorization_role', 'employee')).lower()
        try:
            auth_role = AuthorizationRole(role_str)
        except ValueError:
            auth_role = AuthorizationRole.EMPLOYEE
        result[r['employee_id']] = EmployeeRecord(
            employee_id=r['employee_id'],
            google_subject=r.get('google_subject', ''),
            email=r.get('email', ''),
            name=r.get('name', ''),
            department=r.get('department', 'Engineering'),
            team=r.get('team', 'Payments'),
            job_role=r.get('job_role', 'Software Engineer'),
            authorization_role=auth_role,
            manager_id=r.get('manager_id'),
            location=r.get('location', 'HQ'),
            joining_date=str(r.get('joining_date', '2026-09-01')),
            onboarding_status=r.get('onboarding_status', 'IN_PROGRESS'),
            is_day_one=bool(r.get('is_day_one', False)),
            assigned_buddy_name=r.get('assigned_buddy_name', 'Priya Nair'),
            assigned_buddy_email=r.get('assigned_buddy_email', 'priya.nair@company.com'),
            onboarding_track=r.get('onboarding_track', 'Backend'),
        )
    return result

class DynamicEmployees(dict):
    """Dynamic dictionary backed directly by database table employees."""
    def __getitem__(self, key):
        row = db.query_one('SELECT * FROM employees WHERE employee_id = ? OR email = ? OR google_subject = ?', (key, key, key))
        if row:
            role_str = str(row.get('authorization_role', 'employee')).lower()
            try:
                auth_role = AuthorizationRole(role_str)
            except ValueError:
                auth_role = AuthorizationRole.EMPLOYEE
            return EmployeeRecord(
                employee_id=row['employee_id'],
                google_subject=row.get('google_subject', ''),
                email=row.get('email', ''),
                name=row.get('name', ''),
                department=row.get('department', 'Engineering'),
                team=row.get('team', 'Payments'),
                job_role=row.get('job_role', 'Software Engineer'),
                authorization_role=auth_role,
                manager_id=row.get('manager_id'),
                location=row.get('location', 'HQ'),
                joining_date=str(row.get('joining_date', '2026-09-01')),
                onboarding_status=row.get('onboarding_status', 'IN_PROGRESS'),
                is_day_one=bool(row.get('is_day_one', False)),
                assigned_buddy_name=row.get('assigned_buddy_name', 'Priya Nair'),
                assigned_buddy_email=row.get('assigned_buddy_email', 'priya.nair@company.com'),
                onboarding_track=row.get('onboarding_track', 'Backend'),
            )
        raise KeyError(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
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
        return bool(db.query_one('SELECT 1 FROM employees WHERE employee_id = ? OR email = ? OR google_subject = ?', (key, key, key)))

    def __setitem__(self, key, emp):
        role_val = emp.authorization_role.value if hasattr(emp.authorization_role, 'value') else str(emp.authorization_role)
        db.execute(
            'INSERT OR REPLACE INTO employees '
            '(employee_id, google_subject, email, name, department, team, job_role, authorization_role, manager_id, location, joining_date, onboarding_status, is_day_one, assigned_buddy_name, assigned_buddy_email, onboarding_track) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (emp.employee_id, emp.google_subject, emp.email, emp.name, emp.department, emp.team, emp.job_role, role_val, emp.manager_id, emp.location, emp.joining_date, emp.onboarding_status, int(emp.is_day_one), emp.assigned_buddy_name, emp.assigned_buddy_email, emp.onboarding_track)
        )

EMPLOYEES = DynamicEmployees()

class DynamicTasks(dict):
    """Dynamic task dictionary backed directly by database table employee_onboarding_tasks."""
    def __getitem__(self, emp_id):
        rows = db.query('SELECT * FROM employee_onboarding_tasks WHERE employee_id = ? ORDER BY due_days_after_start ASC', (emp_id,))
        tasks = []
        for r in rows:
            stat_str = r.get('status', 'PENDING').upper()
            try:
                task_stat = TaskStatus(stat_str)
            except ValueError:
                task_stat = TaskStatus.PENDING
            tasks.append(
                OnboardingTask(
                    task_id=r['task_id'],
                    title=r['title'],
                    description=r['description'],
                    status=task_stat,
                    due_days_after_start=r.get('due_days_after_start', 1) or 1,
                    completed_at=r.get('completed_at'),
                    category=r.get('category', 'General'),
                    action_link=r.get('action_link')
                )
            )
        return tasks

    def get(self, emp_id, default=None):
        res = self[emp_id]
        return res if res else (default if default is not None else [])

ONBOARDING_TASKS = DynamicTasks()

class DynamicTimesheets(dict):
    """Dynamic timesheets dictionary backed directly by database table timesheets."""
    def __getitem__(self, emp_id):
        rows = db.query('SELECT * FROM timesheets WHERE employee_id = ? ORDER BY due_date DESC', (emp_id,))
        sheets = []
        for r in rows:
            stat_str = r.get('status', 'PENDING').upper()
            try:
                ts_stat = TimesheetStatus(stat_str)
            except ValueError:
                ts_stat = TimesheetStatus.PENDING
            sheets.append(
                TimesheetRecord(
                    timesheet_id=r['timesheet_id'],
                    employee_id=r['employee_id'],
                    period_start=r['period_start'],
                    period_end=r['period_end'],
                    hours_logged=float(r.get('hours_logged', 40.0)),
                    status=ts_stat,
                    due_date=r['due_date']
                )
            )
        return sheets

    def get(self, emp_id, default=None):
        res = self[emp_id]
        return res if res else (default if default is not None else [])

    def items(self):
        emp_ids = [r['employee_id'] for r in db.query('SELECT DISTINCT employee_id FROM timesheets')]
        return [(eid, self[eid]) for eid in emp_ids]

TIMESHEETS = DynamicTimesheets()

def get_all_incidents() -> List[IncidentRecord]:
    rows = db.query('SELECT * FROM incidents ORDER BY created_at DESC')
    incidents = []
    for r in rows:
        sev_str = r.get('severity', 'MEDIUM').upper()
        try:
            sev = IncidentSeverity(sev_str)
        except ValueError:
            sev = IncidentSeverity.MEDIUM
        incidents.append(
            IncidentRecord(
                incident_id=r['incident_id'],
                created_by=r['created_by'],
                category=r['category'],
                summary=r['summary'],
                severity=sev,
                status=r.get('status', 'OPEN'),
                assigned_team=r.get('assigned_team', 'IT-Support'),
                created_at=r.get('created_at') or '',
                jira_key=r.get('jira_key'),
                jira_url=r.get('jira_url')
            )
        )
    return incidents

class DynamicIncidents(list):
    """Dynamic incident list backed directly by database table incidents."""
    def __iter__(self):
        return iter(get_all_incidents())
    def __len__(self):
        return len(get_all_incidents())
    def append(self, inc):
        sev_val = inc.severity.value if hasattr(inc.severity, 'value') else str(inc.severity)
        db.execute(
            'INSERT OR REPLACE INTO incidents (incident_id, created_by, category, summary, severity, status, assigned_team, created_at, jira_key, jira_url) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (inc.incident_id, inc.created_by, inc.category, inc.summary, sev_val, inc.status, inc.assigned_team, inc.created_at, inc.jira_key, inc.jira_url)
        )

INCIDENTS = DynamicIncidents()

def get_all_team_directory():
    return db.query('SELECT * FROM team_directory_mesh')

TEAM_DIRECTORY = get_all_team_directory()

def get_all_knowledge_catalog() -> List[KnowledgeAsset]:
    assets = db.query('SELECT * FROM knowledge_assets ORDER BY document_id ASC')
    result = []
    for a in assets:
        chunks_rows = db.query('SELECT * FROM knowledge_chunks WHERE document_id = ? ORDER BY chunk_index ASC', (a['document_id'],))
        chunks = [
            KnowledgeChunk(
                chunk_id=c['chunk_id'],
                document_id=c['document_id'],
                content=c['content'],
                access_level=c['access_level'],
                team=c['team'],
                chunk_index=c['chunk_index']
            )
            for c in chunks_rows
        ]
        result.append(
            KnowledgeAsset(
                document_id=a['document_id'],
                title=a['title'],
                source=a.get('source', ''),
                gcs_uri=a.get('gcs_uri', ''),
                team=a['team'],
                access_level=a['access_level'],
                document_type=a.get('document_type', 'Guide'),
                owner=a.get('owner', 'Engineering'),
                description=a.get('description', ''),
                chunks=chunks
            )
        )
    return result

KNOWLEDGE_CATALOG = get_all_knowledge_catalog()
KNOWLEDGE_INSIGHTS = []
