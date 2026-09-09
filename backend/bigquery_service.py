#!/usr/bin/env python3
"""
Company AI Assistant: Google BigQuery Enterprise Data Service
Direct integration with BigQuery for querying employee directories,
onboarding tasks, knowledge mesh catalog, and executing DML updates.
Fully optimized for Google Cloud Run runtime using Instance Metadata Service.
"""

import os
import sys
import json
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, Any, Optional, List
from backend.config import get_config_val

class BigQueryService:
    """
    Executes SQL queries and DML updates directly against BigQuery dataset (employee_ai).
    Uses the Cloud Run Service Account token via the GCP Metadata Server.
    """

    _cached_token: Optional[str] = None
    _token_expiry: float = 0.0

    @classmethod
    def get_project_id(cls) -> str:
        return get_config_val("GCP_PROJECT_ID", "patchamomma-505416")

    @classmethod
    def get_dataset(cls) -> str:
        return get_config_val("BIGQUERY_DATASET", "employee_ai")

    @classmethod
    def get_gcp_access_token(cls) -> Optional[str]:
        """
        Retrieves GCP OAuth2 access token for BigQuery API calls.
        Precedence:
        1. Explicit environment variable GCP_ACCESS_TOKEN
        2. GCP Instance Metadata Server (Cloud Run / Compute Engine native)
        """
        if os.environ.get("GCP_ACCESS_TOKEN"):
            return os.environ.get("GCP_ACCESS_TOKEN")

        import time
        now = time.time()
        if cls._cached_token and now < cls._token_expiry:
            return cls._cached_token

        # Query metadata server in Cloud Run
        try:
            req = urllib.request.Request(
                "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
                headers={"Metadata-Flavor": "Google"}
            )
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                token = data.get("access_token")
                expires_in = data.get("expires_in", 3600)
                cls._cached_token = token
                cls._token_expiry = now + expires_in - 60
                return token
        except Exception:
            return None

    @classmethod
    def execute_query(cls, sql: str) -> Dict[str, Any]:
        """
        Executes a SQL statement via the BigQuery REST API (v2 query endpoint).
        Returns a dict with rows, fields, totalRows, or error.
        """
        project_id = cls.get_project_id()
        token = cls.get_gcp_access_token()

        url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/queries"
        payload = json.dumps({
            "query": sql,
            "useLegacySql": False,
            "timeoutMs": 10000
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "x-goog-user-project": project_id
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))

                # Parse rows if present
                schema_fields = [f.get("name") for f in data.get("schema", {}).get("fields", [])]
                raw_rows = data.get("rows", [])
                parsed_rows = []

                for r in raw_rows:
                    row_vals = [f.get("v") for f in r.get("f", [])]
                    row_dict = dict(zip(schema_fields, row_vals))
                    parsed_rows.append(row_dict)

                return {
                    "success": True,
                    "rows": parsed_rows,
                    "total_rows": int(data.get("totalRows", len(parsed_rows))),
                    "job_complete": data.get("jobComplete", True),
                    "num_dml_affected_rows": data.get("numDmlAffectedRows")
                }
        except urllib.error.HTTPError as he:
            body = ""
            try:
                body = he.read().decode("utf-8")
            except Exception:
                pass
            print(f"[BigQueryService] HTTP {he.code} executing query: {body[:150]}", file=sys.stderr)
            return {
                "success": False,
                "error": f"HTTP {he.code}: {he.reason}",
                "error_details": body,
                "rows": []
            }
        except Exception as e:
            print(f"[BigQueryService] Error executing query: {e}", file=sys.stderr)
            return {
                "success": False,
                "error": str(e),
                "rows": []
            }

    @classmethod
    def get_employee(cls, employee_id: str) -> Optional[Dict[str, Any]]:
        """
        Queries employee directory directly from BigQuery.
        Table: `patchamomma-505416.employee_ai.employees`
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
            return res["rows"][0]
        return None

    @classmethod
    def get_all_employees(cls) -> List[Dict[str, Any]]:
        """
        Retrieves all employee records from BigQuery table `employees`.
        """
        project = cls.get_project_id()
        dataset = cls.get_dataset()
        sql = f"SELECT * FROM `{project}.{dataset}.employees` ORDER BY employee_id ASC"
        res = cls.execute_query(sql)
        if res.get("success"):
            return res.get("rows", [])
        return []

    @classmethod
    def update_employee_status(cls, employee_id: str, status: str) -> bool:
        """
        Executes DML update on BigQuery employee record.
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
        Queries employee onboarding tasks from BigQuery.
        Table: `patchamomma-505416.employee_ai.employee_onboarding_tasks`
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
        Executes DML update in BigQuery to mark an onboarding task completed.
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
    def test_connection(cls) -> Dict[str, Any]:
        """
        Tests connection to BigQuery, checks dataset existence, and validates IAM permissions.
        """
        project_id = cls.get_project_id()
        dataset = cls.get_dataset()
        token = cls.get_gcp_access_token()

        result = {
            "project_id": project_id,
            "dataset": dataset,
            "connected": False,
            "authenticated": token is not None,
            "status": "Checking...",
            "iam_role_required": "roles/bigquery.dataEditor and roles/bigquery.jobUser",
            "details": {}
        }

        url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/datasets/{dataset}"
        headers = {
            "x-goog-user-project": project_id
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                result["connected"] = True
                result["status"] = f"Connected successfully to BigQuery dataset: {dataset}"
                result["details"] = {
                    "location": data.get("location"),
                    "lastModifiedTime": data.get("lastModifiedTime")
                }
        except urllib.error.HTTPError as he:
            body = ""
            try:
                body = he.read().decode("utf-8")
            except Exception:
                pass

            if he.code == 403:
                result["status"] = "BigQuery API reachable; IAM roles 'roles/bigquery.dataEditor' and 'roles/bigquery.jobUser' required on Cloud Run Service Account."
                result["error_code"] = 403
            elif he.code == 404:
                result["status"] = f"BigQuery API reachable; dataset '{dataset}' not found. Run bigquery/tables.sql to create."
                result["error_code"] = 404
            else:
                result["status"] = f"BigQuery HTTP {he.code}: {he.reason}"
        except Exception as e:
            result["status"] = f"Connection check failed: {str(e)}"

        return result
