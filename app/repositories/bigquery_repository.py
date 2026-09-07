"""
Google BigQuery Repository Implementation.
Used when REPOSITORY_BACKEND=bigquery for live GCP Cloud Run production.
"""

import json
import logging
import uuid
from decimal import Decimal
from datetime import date, datetime, timezone
from typing import Dict, List, Optional, Any

from app.config import settings
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

logger = logging.getLogger("patchamomma.repository.bigquery")

try:
    from google.cloud import bigquery
except ImportError:
    bigquery = None


class BigQueryRepositoryBase:
    def __init__(self):
        self._client: Optional[bigquery.Client] = None
        if bigquery:
            try:
                self._client = bigquery.Client(project=settings.GCP_PROJECT_ID)
            except Exception as e:
                logger.warning(f"Could not initialize BigQuery client: {e}")

    @property
    def client(self) -> bigquery.Client:
        if not self._client:
            raise RuntimeError("BigQuery client is not initialized or google-cloud-bigquery is unavailable.")
        return self._client

    def _row_to_dict(self, row) -> Dict[str, Any]:
        """Converts BigQuery row to a clean dictionary serializing date, datetime, and Decimal values."""
        d = dict(row.items())
        for k, v in d.items():
            if isinstance(v, (datetime, date)):
                d[k] = v.isoformat()
            elif isinstance(v, Decimal):
                d[k] = float(v)
        return d


class BigQueryEmployeeRepository(BigQueryRepositoryBase, IEmployeeRepository):
    def get_by_google_subject(self, google_subject: str) -> Optional[EmployeeRecord]:
        query = f"""
            SELECT employee_id, google_subject, email, name, department, team,
                   job_role, authorization_role, manager_id, location, joining_date,
                   onboarding_status, is_day_one, assigned_buddy_name, assigned_buddy_email, onboarding_track
            FROM `{settings.BIGQUERY_DATASET}.employees`
            WHERE google_subject = @sub
            LIMIT 1
        """
        job_config = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter("sub", "STRING", google_subject)])
        rows = list(self.client.query(query, job_config=job_config).result())
        if rows:
            return EmployeeRecord(**self._row_to_dict(rows[0]))
        return None

    def get_by_id(self, employee_id: str) -> Optional[EmployeeRecord]:
        query = f"""
            SELECT * FROM `{settings.BIGQUERY_DATASET}.employees`
            WHERE employee_id = @emp_id
            LIMIT 1
        """
        job_config = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter("emp_id", "STRING", employee_id)])
        rows = list(self.client.query(query, job_config=job_config).result())
        if rows:
            return EmployeeRecord(**self._row_to_dict(rows[0]))
        return None

    def get_by_team(self, team: str) -> List[EmployeeRecord]:
        query = f"""
            SELECT * FROM `{settings.BIGQUERY_DATASET}.employees`
            WHERE LOWER(team) = LOWER(@team)
        """
        job_config = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter("team", "STRING", team)])
        return [EmployeeRecord(**self._row_to_dict(r)) for r in self.client.query(query, job_config=job_config).result()]

    def get_by_manager_id(self, manager_id: str) -> List[EmployeeRecord]:
        query = f"""
            SELECT * FROM `{settings.BIGQUERY_DATASET}.employees`
            WHERE manager_id = @mgr_id
        """
        job_config = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter("mgr_id", "STRING", manager_id)])
        return [EmployeeRecord(**self._row_to_dict(r)) for r in self.client.query(query, job_config=job_config).result()]

    def list_all(self) -> List[EmployeeRecord]:
        query = f"SELECT * FROM `{settings.BIGQUERY_DATASET}.employees`"
        return [EmployeeRecord(**self._row_to_dict(r)) for r in self.client.query(query).result()]


class BigQueryOnboardingRepository(BigQueryRepositoryBase, IOnboardingRepository):
    def get_checklist(self, employee_id: str) -> Optional[OnboardingChecklist]:
        query = f"""
            SELECT task_id, title, description, status, due_days_after_start,
                   completed_at, category, action_link
            FROM `{settings.BIGQUERY_DATASET}.employee_onboarding_tasks`
            WHERE employee_id = @emp_id
            ORDER BY due_days_after_start ASC
        """
        job_config = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter("emp_id", "STRING", employee_id)])
        rows = list(self.client.query(query, job_config=job_config).result())
        if not rows:
            return None

        tasks = [OnboardingTask(**self._row_to_dict(r)) for r in rows]
        completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        next_task = next((t for t in tasks if t.status == TaskStatus.PENDING), None)

        return OnboardingChecklist(
            employee_id=employee_id,
            track="Backend",
            tasks=tasks,
            completed_count=completed,
            total_count=len(tasks),
            next_pending_task=next_task,
        )

    def complete_task(self, employee_id: str, task_id: str) -> bool:
        query = f"""
            UPDATE `{settings.BIGQUERY_DATASET}.employee_onboarding_tasks`
            SET status = 'COMPLETED', completed_at = CURRENT_TIMESTAMP()
            WHERE employee_id = @emp_id AND task_id = @task_id
        """
        job_config = bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("emp_id", "STRING", employee_id),
            bigquery.ScalarQueryParameter("task_id", "STRING", task_id),
        ])
        query_job = self.client.query(query, job_config=job_config)
        query_job.result()
        return query_job.num_dml_affected_rows > 0

    def get_team_progress(self, manager_id: str, team: str) -> List[TeamMemberOnboardingProgress]:
        query = f"""
            SELECT e.employee_id, e.name, e.job_role, e.team,
                   COUNTIF(t.status = 'COMPLETED') as completed_count,
                   COUNT(t.task_id) as total_count,
                   LOGICAL_OR(t.status = 'BLOCKED') as is_blocked
            FROM `{settings.BIGQUERY_DATASET}.employees` e
            LEFT JOIN `{settings.BIGQUERY_DATASET}.employee_onboarding_tasks` t ON e.employee_id = t.employee_id
            WHERE e.manager_id = @mgr_id OR LOWER(e.team) = LOWER(@team)
            GROUP BY e.employee_id, e.name, e.job_role, e.team
        """
        job_config = bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("mgr_id", "STRING", manager_id),
            bigquery.ScalarQueryParameter("team", "STRING", team),
        ])
        results = []
        for r in self.client.query(query, job_config=job_config).result():
            results.append(
                TeamMemberOnboardingProgress(
                    employee_id=r.employee_id,
                    name=r.name,
                    job_role=r.job_role,
                    team=r.team,
                    completed_count=r.completed_count or 0,
                    total_count=r.total_count or 1,
                    pending_tasks=[],
                    is_blocked=bool(r.is_blocked),
                )
            )
        return results


class BigQueryKnowledgeRepository(BigQueryRepositoryBase, IKnowledgeRepository):
    def get_by_id(self, document_id: str) -> Optional[KnowledgeAsset]:
        query = f"SELECT * FROM `{settings.BIGQUERY_DATASET}.knowledge_assets` WHERE document_id = @doc_id"
        job_config = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter("doc_id", "STRING", document_id)])
        rows = list(self.client.query(query, job_config=job_config).result())
        if rows:
            return KnowledgeAsset(**self._row_to_dict(rows[0]))
        return None

    def search_authorized(self, query: str, user_team: str, user_role: AuthorizationRole) -> List[KnowledgeChunk]:
        """
        SQL PRE-RETRIEVAL ACL:
        Applies SQL WHERE clause restricting team domain and access level before pulling rows.
        """
        sql = f"""
            SELECT c.chunk_id, c.document_id, c.chunk_index, c.content, c.team, c.access_level
            FROM `{settings.BIGQUERY_DATASET}.knowledge_chunks` c
            JOIN `{settings.BIGQUERY_DATASET}.knowledge_assets` a ON c.document_id = a.document_id
            WHERE (a.team = 'ALL' OR LOWER(a.team) = LOWER(@user_team))
              AND (
                a.access_level = 'employee'
                OR (@user_role = 'manager' AND a.access_level IN ('employee', 'manager'))
                OR (@user_role = 'hr' AND a.access_level IN ('employee', 'hr'))
                OR (@user_role = 'it' AND a.access_level IN ('employee', 'it'))
              )
        """
        job_config = bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("user_team", "STRING", user_team),
            bigquery.ScalarQueryParameter("user_role", "STRING", user_role.value),
        ])
        rows = list(self.client.query(sql, job_config=job_config).result())
        return [KnowledgeChunk(**self._row_to_dict(r)) for r in rows]


class BigQueryOperationsRepository(BigQueryRepositoryBase, IOperationsRepository):
    def get_timesheets(self, employee_id: str) -> List[TimesheetRecord]:
        query = f"SELECT * FROM `{settings.BIGQUERY_DATASET}.timesheets` WHERE employee_id = @emp_id"
        job_config = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter("emp_id", "STRING", employee_id)])
        return [TimesheetRecord(**self._row_to_dict(r)) for r in self.client.query(query, job_config=job_config).result()]

    def create_incident(self, incident: IncidentRecord) -> IncidentRecord:
        table_ref = f"{settings.GCP_PROJECT_ID}.{settings.BIGQUERY_DATASET}.incidents"
        errors = self.client.insert_rows_json(table_ref, [incident.model_dump()])
        if errors:
            logger.error(f"BigQuery incident insert errors: {errors}")
        return incident

    def get_escalation_contact(self, domain: str) -> Optional[TeamEscalationContact]:
        query = f"""
            SELECT system_domain as domain, primary_lead_name, primary_email, primary_on_vacation,
                   backup_lead_name, backup_email, backup_on_vacation, general_team_channel as general_channel
            FROM `{settings.BIGQUERY_DATASET}.team_directory_mesh`
            WHERE LOWER(system_domain) = LOWER(@domain)
            LIMIT 1
        """
        job_config = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter("domain", "STRING", domain)])
        rows = list(self.client.query(query, job_config=job_config).result())
        if rows:
            return TeamEscalationContact(**self._row_to_dict(rows[0]))
        return None

    def stream_telemetry(self, payload: Dict[str, Any]) -> str:
        table_ref = f"{settings.GCP_PROJECT_ID}.{settings.BIGQUERY_DATASET}.agent_telemetry_friction_log"
        errors = self.client.insert_rows_json(table_ref, [payload])
        if errors:
            logger.error(f"BigQuery telemetry insert errors: {errors}")
        return payload.get("log_id", str(uuid.uuid4()))
