#!/usr/bin/env python3
"""
Company AI Assistant: Master BigQuery Enterprise Integration Service
Directly manages reads and writes for BigQuery tables using the official Google Cloud SDK Client:
  - patchamomma-505416.employee_ai.employees
  - patchamomma-505416.employee_ai.employee_onboarding_tasks
  - patchamomma-505416.employee_ai.knowledge_assets
  - patchamomma-505416.employee_ai.knowledge_chunks
  - patchamomma-505416.employee_ai.timesheets
  - patchamomma-505416.employee_ai.incidents
  - patchamomma-505416.employee_ai.team_directory_mesh
  - patchamomma-505416.employee_ai.agent_telemetry_friction_log
Backed by enterprise database schema and seeds in bigquery/ with automated fallback.
"""

import os
import sys
import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
from backend.config import get_config_val
from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError


class BigQueryService:
    """
    Official SDK client connection manager for Google BigQuery executing queries and DML mutations.
    Provides complete SQL persistence across all enterprise entities natively against Cloud BigQuery.
    """

    @classmethod
    def get_project_id(cls) -> str:
        return get_config_val("GCP_PROJECT_ID", "patchamomma-505416")

    @classmethod
    def get_dataset(cls) -> str:
        return get_config_val("BIGQUERY_DATASET", "employee_ai")

    _LOCAL_SEQUENCE = 11
    _client = None
    _client_attempted = False
    _client_available = False

    @classmethod
    def get_client(cls) -> Optional[bigquery.Client]:
        if cls._client is not None:
            return cls._client
        if cls._client_attempted and not cls._client_available:
            return None

        cls._client_attempted = True
        try:
            import google.auth
            credentials, _ = google.auth.default()
            cls._client = bigquery.Client(project=cls.get_project_id(), credentials=credentials)
            cls._client_available = True
            return cls._client
        except Exception as e:
            cls._client_available = False
            print(f"[BigQueryService] Local/Cloud ADC resolution notice: {e}", file=sys.stderr)
            return None

    @classmethod
    def execute_query(cls, sql: str) -> Dict[str, Any]:
        """
        Executes a SQL statement via the official BigQuery Client SDK directly.
        All production data is queried from and mutated in Cloud BigQuery.
        """
        client = cls.get_client()
        if not client:
            return {
                "success": False,
                "error": "BigQuery client credentials unavailable (using fallback)",
                "rows": [],
                "total_rows": 0,
                "job_complete": False,
                "engine": "cloud_bigquery"
            }

        try:
            query_job = client.query(sql)
            results = query_job.result(timeout=4.0)  # Safe timeout for query execution

            # Parse rows into lists of plain dict objects
            parsed_rows = [dict(row) for row in results]
            
            return {
                "success": True,
                "rows": parsed_rows,
                "total_rows": len(parsed_rows),
                "job_complete": True,
                "num_dml_affected_rows": query_job.num_dml_affected_rows,
                "engine": "cloud_bigquery"
            }
        except Exception as e:
            print(f"[BigQueryService] BigQuery query execution notice: {str(e)}", file=sys.stderr)
            return {
                "success": False,
                "error": str(e),
                "rows": [],
                "total_rows": 0,
                "job_complete": False,
                "engine": "cloud_bigquery"
            }

    @classmethod
    def get_employee(cls, employee_id: str) -> Optional[Dict[str, Any]]:
        """
        Queries employee directory directly from BigQuery / DB table `employees`.
        """
        clean_id = employee_id.replace("'", "\\'")
        project = cls.get_project_id()
        dataset = cls.get_dataset()
        sql = (
            f"SELECT * FROM `{project}.{dataset}.employees` "
            f"WHERE employee_id = '{clean_id}' OR email = '{clean_id}' OR google_subject = '{clean_id}' "
            f"LIMIT 1"
        )
        res = cls.execute_query(sql)
        if res.get("success") and res.get("rows"):
            return res["rows"]
        return None

    @classmethod
    def get_all_employees(cls) -> List[Dict[str, Any]]:
        """
        Retrieves all employee records from BigQuery / DB table `employees`.
        """
        project = cls.get_project_id()
        dataset = cls.get_dataset()
        sql = f"SELECT * FROM `{project}.{dataset}.employees` ORDER BY employee_id ASC"
        res = cls.execute_query(sql)
        if res.get("success"):
            return res.get("rows", [])
        return []

    @classmethod
    def allocate_next_employee_id(cls, year: int = 2026) -> str:
        """
        Allocates the next incremental employee ID (e.g. EMP-2026-011) using the
        employee_id_sequences table or table MAX() fallback.
        """
        project = cls.get_project_id()
        dataset = cls.get_dataset()
        next_seq = None

        # 1. Try to read from employee_id_sequences in BigQuery
        try:
            seq_sql = f"SELECT next_sequence FROM `{project}.{dataset}.employee_id_sequences` WHERE sequence_name = 'employee' AND id_year = {year} LIMIT 1"
            res = cls.execute_query(seq_sql)
            if res.get("success") and res.get("rows"):
                next_seq = int(res["rows"][0]["next_sequence"])
                # Increment the sequence in BigQuery
                update_sql = f"UPDATE `{project}.{dataset}.employee_id_sequences` SET next_sequence = {next_seq + 1} WHERE sequence_name = 'employee' AND id_year = {year}"
                cls.execute_query(update_sql)
        except Exception as e:
            print(f"[BigQueryService] Sequence query notice: {e}", file=sys.stderr)

        # 2. Fallback: inspect max employee_id in employees table
        if next_seq is None:
            try:
                max_sql = f"SELECT employee_id FROM `{project}.{dataset}.employees` WHERE employee_id LIKE 'EMP-{year}-%' ORDER BY employee_id DESC LIMIT 1"
                res = cls.execute_query(max_sql)
                if res.get("success") and res.get("rows"):
                    last_id = str(res["rows"][0]["employee_id"])
                    match = re.search(r"EMP-\d{4}-(\d+)", last_id)
                    if match:
                        next_seq = int(match.group(1)) + 1
            except Exception as e:
                print(f"[BigQueryService] Max ID query notice: {e}", file=sys.stderr)

        # 3. Memory sequence fallback (auto-increments locally)
        if next_seq is None or next_seq < 1:
            next_seq = cls._LOCAL_SEQUENCE
            cls._LOCAL_SEQUENCE += 1
        else:
            if next_seq >= cls._LOCAL_SEQUENCE:
                cls._LOCAL_SEQUENCE = next_seq + 1

        return f"EMP-{year}-{next_seq:03d}"

    @classmethod
    def create_employee(cls, emp_dict: Dict[str, Any]) -> bool:
        """
        Inserts a new employee record into BigQuery table `employees`.
        """
        emp_id = str(emp_dict.get("employee_id", "")).replace("'", "\\'")
        google_sub = str(emp_dict.get("google_subject", "")).replace("'", "\\'")
        email = str(emp_dict.get("email", "")).replace("'", "\\'")
        name = str(emp_dict.get("name", "")).replace("'", "\\'")
        department = str(emp_dict.get("department", "Engineering")).replace("'", "\\'")
        team = str(emp_dict.get("team", "Unassigned")).replace("'", "\\'")
        job_role = str(emp_dict.get("job_role", "Software Engineer")).replace("'", "\\'")
        auth_role = str(emp_dict.get("authorization_role", "employee")).replace("'", "\\'")
        mgr_val = str(emp_dict.get('manager_id')).replace("'", "\\'") if emp_dict.get("manager_id") else None
        manager_id = f"'{mgr_val}'" if mgr_val else "NULL"
        location = str(emp_dict.get("location", "HQ")).replace("'", "\\'")
        joining_date = str(emp_dict.get("joining_date", datetime.utcnow().strftime("%Y-%m-%d"))).replace("'", "\\'")
        onboarding_status = str(emp_dict.get("onboarding_status", "NOT_STARTED")).replace("'", "\\'")
        is_day_one = "TRUE" if emp_dict.get("is_day_one", True) else "FALSE"
        bname_val = str(emp_dict.get('assigned_buddy_name')).replace("'", "\\'") if emp_dict.get("assigned_buddy_name") else None
        buddy_name = f"'{bname_val}'" if bname_val else "NULL"
        bemail_val = str(emp_dict.get('assigned_buddy_email')).replace("'", "\\'") if emp_dict.get("assigned_buddy_email") else None
        buddy_email = f"'{bemail_val}'" if bemail_val else "NULL"
        track = str(emp_dict.get("onboarding_track", "General")).replace("'", "\\'")

        project = cls.get_project_id()
        dataset = cls.get_dataset()
        sql = (
            f"INSERT INTO `{project}.{dataset}.employees` "
            f"(employee_id, google_subject, email, name, department, team, job_role, authorization_role, manager_id, location, joining_date, onboarding_status, is_day_one, assigned_buddy_name, assigned_buddy_email, onboarding_track) "
            f"VALUES ('{emp_id}', '{google_sub}', '{email}', '{name}', '{department}', '{team}', '{job_role}', '{auth_role}', {manager_id}, '{location}', DATE('{joining_date}'), '{onboarding_status}', {is_day_one}, {buddy_name}, {buddy_email}, '{track}')"
        )
        res = cls.execute_query(sql)
        return bool(res.get("success"))

    @classmethod
    def create_employee_tasks(cls, employee_id: str, tasks: List[Dict[str, Any]]) -> bool:
        """
        Inserts initial onboarding tasks for an employee into `employee_onboarding_tasks`.
        """
        if not tasks:
            return True
        project = cls.get_project_id()
        dataset = cls.get_dataset()
        value_rows = []
        for t in tasks:
            task_id = str(t.get("task_id", "")).replace("'", "\\'")
            clean_emp = employee_id.replace("'", "\\'")
            title = str(t.get("title", "")).replace("'", "\\'")
            desc = str(t.get("description", "")).replace("'", "\\'")
            status = str(t.get("status", "PENDING")).replace("'", "\\'")
            due_days = int(t.get("due_days_after_start", 1) or 1)
            completed_at = f"TIMESTAMP('{t.get('completed_at')}')" if t.get("completed_at") else "NULL"
            cat = str(t.get("category", "General")).replace("'", "\\'")
            act_val = str(t.get('action_link')).replace("'", "\\'") if t.get("action_link") else None
            action_link = f"'{act_val}'" if act_val else "NULL"
            value_rows.append(f"('{task_id}', '{clean_emp}', '{title}', '{desc}', '{status}', {due_days}, {completed_at}, '{cat}', {action_link})")
        
        sql = (
            f"INSERT INTO `{project}.{dataset}.employee_onboarding_tasks` "
            f"(task_id, employee_id, title, description, status, due_days_after_start, completed_at, category, action_link) "
            f"VALUES {', '.join(value_rows)}"
        )
        res = cls.execute_query(sql)
        return bool(res.get("success"))

    @classmethod
    def update_employee_status(cls, employee_id: str, status: str) -> bool:
        """
        Executes DML update on employee record.
        """
        clean_id = employee_id.replace("'", "\\'")
        clean_status = status.replace("'", "\\'")
        project = cls.get_project_id()
        dataset = cls.get_dataset()
        sql = f"UPDATE `{project}.{dataset}.employees` SET onboarding_status = '{clean_status}' WHERE employee_id = '{clean_id}'"
        res = cls.execute_query(sql)
        return bool(res.get("success"))

    @classmethod
    def get_employee_tasks(cls, employee_id: str) -> List[Dict[str, Any]]:
        """
        Queries employee onboarding tasks from BigQuery / DB table `employee_onboarding_tasks`.
        """
        clean_id = employee_id.replace("'", "\\'")
        project = cls.get_project_id()
        dataset = cls.get_dataset()
        sql = (
            f"SELECT task_id, employee_id, title, description, status, due_days_after_start, completed_at, category, action_link "
            f"FROM `{project}.{dataset}.employee_onboarding_tasks` "
            f"WHERE employee_id = '{clean_id}' ORDER BY due_days_after_start ASC"
        )
        res = cls.execute_query(sql)
        if res.get("success"):
            return res.get("rows", [])
        return []

    @classmethod
    def update_task_status(cls, employee_id: str, task_id: str, status: str = "COMPLETED") -> bool:
        """
        Executes DML update to mark an onboarding task completed.
        """
        clean_emp = employee_id.replace("'", "\\'")
        clean_task = task_id.replace("'", "\\'")
        clean_status = status.replace("'", "\\'")
        project = cls.get_project_id()
        dataset = cls.get_dataset()
        sql = (
            f"UPDATE `{project}.{dataset}.employee_onboarding_tasks` "
            f"SET status = '{clean_status}', completed_at = CURRENT_TIMESTAMP() "
            f"WHERE employee_id = '{clean_emp}' AND task_id = '{clean_task}'"
        )
        res = cls.execute_query(sql)
        return bool(res.get("success"))

    @classmethod
    def get_timesheet_status(cls, employee_id: str) -> List[Dict[str, Any]]:
        """
        Queries timesheet records from BigQuery / DB table `timesheets`.
        """
        clean_id = employee_id.replace("'", "\\'")
        project = cls.get_project_id()
        dataset = cls.get_dataset()
        sql = (
            f"SELECT * FROM `{project}.{dataset}.timesheets` "
            f"WHERE employee_id = '{clean_id}' ORDER BY due_date DESC"
        )
        res = cls.execute_query(sql)
        if res.get("success"):
            return res.get("rows", [])
        return []

    @classmethod
    def update_timesheet(cls, employee_id: str, hours_logged: float, status: str = "SUBMITTED") -> bool:
        """
        Updates timesheet record in BigQuery / DB table `timesheets`.
        """
        clean_id = employee_id.replace("'", "\\'")
        clean_status = status.replace("'", "\\'")
        project = cls.get_project_id()
        dataset = cls.get_dataset()
        sql = (
            f"UPDATE `{project}.{dataset}.timesheets` "
            f"SET status = '{clean_status}', hours_logged = {hours_logged} "
            f"WHERE employee_id = '{clean_id}'"
        )
        res = cls.execute_query(sql)
        return bool(res.get("success"))

    @classmethod
    def search_knowledge_chunks(cls, query: str, team: str = "ALL", role: str = "EMPLOYEE") -> List[Dict[str, Any]]:
        """
        Queries authorized knowledge chunks with RBAC clearance filtering.
        """
        clean_q = query.replace("'", "\\'").lower()
        project = cls.get_project_id()
        dataset = cls.get_dataset()
        is_mgr = role.upper() in ["MANAGER", "HR", "ADMIN"]
        access_filter = "" if is_mgr else "AND access_level != 'manager'"
        team_filter = "" if team.upper() == "ALL" else f"AND (team = 'ALL' OR LOWER(team) = '{team.lower()}')"

        sql = (
            f"SELECT chunk_id, document_id, team, access_level, chunk_index, content "
            f"FROM `{project}.{dataset}.knowledge_chunks` "
            f"WHERE 1=1 {access_filter} {team_filter} "
            f"ORDER BY chunk_index ASC"
        )
        res = cls.execute_query(sql)
        if res.get("success"):
            rows = res.get("rows", [])
            words = [w for w in clean_q.split() if len(w) > 2]
            if not words:
                return rows[:5]
            filtered = [
                r for r in rows
                if any(w in r.get("content", "").lower() for w in words)
            ]
            return filtered if filtered else rows[:3]
        return []

    @classmethod
    def get_team_escalation(cls, domain: str = "") -> List[Dict[str, Any]]:
        """
        Retrieves team escalation directory mesh from table `team_directory_mesh`.
        """
        project = cls.get_project_id()
        dataset = cls.get_dataset()
        sql = f"SELECT * FROM `{project}.{dataset}.team_directory_mesh`"
        res = cls.execute_query(sql)
        if res.get("success"):
            return res.get("rows", [])
        return []

    @classmethod
    def create_incident(cls, incident: Dict[str, Any]) -> bool:
        """
        Inserts new incident record into BigQuery / DB table `incidents`.
        """
        inc_id = incident.get("incident_id", "").replace("'", "\\'")
        creator = incident.get("created_by", "").replace("'", "\\'")
        cat = incident.get("category", "").replace("'", "\\'")
        summary = incident.get("summary", "").replace("'", "\\'")
        sev = incident.get("severity", "MEDIUM").replace("'", "\\'")
        stat = incident.get("status", "OPEN").replace("'", "\\'")
        team = incident.get("assigned_team", "IT-Support").replace("'", "\\'")
        created_at = incident.get("created_at") or datetime.utcnow().isoformat() + "Z"

        project = cls.get_project_id()
        dataset = cls.get_dataset()
        sql = (
            f"INSERT INTO `{project}.{dataset}.incidents` "
            f"(incident_id, created_by, category, summary, severity, status, assigned_team, created_at) "
            f"VALUES ('{inc_id}', '{creator}', '{cat}', '{summary}', '{sev}', '{stat}', '{team}', '{created_at}')"
        )
        res = cls.execute_query(sql)
        return bool(res.get("success"))

    @classmethod
    def get_incidents(cls) -> List[Dict[str, Any]]:
        """
        Queries all incident records from BigQuery / DB table `incidents`.
        """
        project = cls.get_project_id()
        dataset = cls.get_dataset()
        sql = f"SELECT * FROM `{project}.{dataset}.incidents` ORDER BY created_at DESC"
        res = cls.execute_query(sql)
        if res.get("success"):
            return res.get("rows", [])
        return []

    @classmethod
    def record_friction_log(cls, employee_id: str, query: str, missing_domain: str, severity: str = "MEDIUM") -> bool:
        """
        Inserts agent friction telemetry into table `agent_telemetry_friction_log`.
        """
        import uuid
        log_id = f"FRIC-{str(uuid.uuid4())[:8]}"
        clean_emp = employee_id.replace("'", "\\'")
        clean_q = query.replace("'", "\\'")
        clean_dom = missing_domain.replace("'", "\\'")
        clean_sev = severity.replace("'", "\\'")

        project = cls.get_project_id()
        dataset = cls.get_dataset()
        sql = (
            f"INSERT INTO `{project}.{dataset}.agent_telemetry_friction_log` "
            f"(log_id, employee_id, user_query, detected_gap_domain, friction_severity, created_at) "
            f"VALUES ('{log_id}', '{clean_emp}', '{clean_q}', '{clean_dom}', '{clean_sev}', CURRENT_TIMESTAMP())"
        )
        res = cls.execute_query(sql)
        return bool(res.get("success"))

    @classmethod
    def test_connection(cls) -> Dict[str, Any]:
        """
        Tests connection to BigQuery dataset using the official client library.
        """
        project_id = cls.get_project_id()
        dataset_id = cls.get_dataset()

        result = {
            "project_id": project_id,
            "dataset": dataset_id,
            "connected": False,
            "status": "Checking...",
            "details": {}
        }

        try:
            client = bigquery.Client(project=project_id)
            dataset = client.get_dataset(f"{project_id}.{dataset_id}")
            
            result["connected"] = True
            result["status"] = f"Connected successfully to BigQuery dataset: {dataset_id}"
            result["details"] = {
                "location": dataset.location,
                "created": dataset.created.isoformat() if dataset.created else None,
                "modified": dataset.modified.isoformat() if dataset.modified else None
            }
        except Exception as e:
            result["connected"] = False
            result["status"] = f"BigQuery SDK Resolution Failure: {str(e)}"

        return result
