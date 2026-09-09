#!/usr/bin/env python3
"""
Company AI Assistant: Enterprise Python Cloud Firestore Persistence Layer
Direct integration with Google Cloud Firestore database:
ai-studio-onboardingemploy-b1158660-8824-4e90-b842-3a0f086d1796
No local files or in-memory fallback caches. All data is read and written directly
to the Cloud Firestore database via the Firestore REST API.
"""

import json
import os
import sys
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, Any, Optional, List
from datetime import datetime
from backend.config import get_config_val

class FirestoreManager:
    """
    Manages persistent Cloud Firestore read/write operations for employee sessions,
    chat histories, checklists, timesheets, and support incidents directly against Cloud Firestore.
    """

    def __init__(self):
        self.project_id = get_config_val("GCP_PROJECT_ID", "patchamomma-505416")
        self.database_id = get_config_val("FIRESTORE_DATABASE_ID", "onboarding-employee-assistant-firestore-database")
        self.api_key = os.environ.get("FIREBASE_API_KEY", "")
        self._cached_token: Optional[str] = None
        self._token_expiry: float = 0.0

    def _get_auth_token(self) -> Optional[str]:
        """
        Retrieves GCP OAuth2 token from instance metadata server in Cloud Run if available.
        """
        if os.environ.get("GCP_ACCESS_TOKEN"):
            return os.environ.get("GCP_ACCESS_TOKEN")

        import time
        now = time.time()
        if self._cached_token and now < self._token_expiry:
            return self._cached_token

        try:
            req = urllib.request.Request(
                "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
                headers={"Metadata-Flavor": "Google"}
            )
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                token = data.get("access_token")
                expires_in = data.get("expires_in", 3600)
                self._cached_token = token
                self._token_expiry = now + expires_in - 60
                return token
        except Exception:
            return None

    @property
    def base_url(self) -> str:
        return (
            f"https://firestore.googleapis.com/v1/projects/{self.project_id}/"
            f"databases/{self.database_id}/documents"
        )

    def _execute_request(self, path: str, method: str = "GET", payload: Optional[bytes] = None) -> Optional[Dict[str, Any]]:
        """
        Executes a Firestore REST API request directly to Google Cloud Firestore.
        Uses OAuth2 Bearer token in Cloud Run, or direct database access.
        """
        clean_path = path.lstrip("/")
        headers = {"Content-Type": "application/json"} if payload else {}
        token = self._get_auth_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"

        url = f"{self.base_url}/{clean_path}"

        try:
            req = urllib.request.Request(url, data=payload, method=method, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as he:
            if he.code != 404:
                print(f"[Firestore] HTTP {he.code} on {method} {clean_path}: {he.reason}", file=sys.stderr)
        except Exception as e:
            print(f"[Firestore] Network error on {method} {clean_path}: {e}", file=sys.stderr)

        return None

    def test_connection(self) -> Dict[str, Any]:
        """
        Tests the live connection to Cloud Firestore and reports collection status.
        """
        result: Dict[str, Any] = {
            "project_id": self.project_id,
            "database_id": self.database_id,
            "connected": False,
            "collections": {},
            "status": "Checking..."
        }
        try:
            checklists_res = self._execute_request("checklists")
            if checklists_res is not None:
                result["connected"] = True
                result["status"] = "Connected successfully to Cloud Firestore"
                chk_docs = checklists_res.get("documents", [])
                result["collections"]["checklists"] = len(chk_docs)

                sess_res = self._execute_request("sessions")
                if sess_res is not None:
                    result["collections"]["sessions"] = len(sess_res.get("documents", []))
            else:
                result["status"] = "Unable to connect to Firestore database"
        except Exception as e:
            result["status"] = f"Connection check failed: {str(e)}"

        return result

    def _python_to_firestore_value(self, val: Any) -> Dict[str, Any]:
        if val is None:
            return {"nullValue": None}
        elif isinstance(val, bool):
            return {"booleanValue": val}
        elif isinstance(val, int):
            return {"integerValue": str(val)}
        elif isinstance(val, float):
            return {"doubleValue": val}
        elif isinstance(val, str):
            return {"stringValue": val}
        elif isinstance(val, list):
            return {"arrayValue": {"values": [self._python_to_firestore_value(v) for v in val]}}
        elif isinstance(val, dict):
            fields = {k: self._python_to_firestore_value(v) for k, v in val.items()}
            return {"mapValue": {"fields": fields}}
        return {"stringValue": str(val)}

    def _firestore_to_python_value(self, fval: Dict[str, Any]) -> Any:
        if not isinstance(fval, dict):
            return fval
        if "nullValue" in fval:
            return None
        if "booleanValue" in fval:
            return fval["booleanValue"]
        if "integerValue" in fval:
            return int(fval["integerValue"])
        if "doubleValue" in fval:
            return float(fval["doubleValue"])
        if "stringValue" in fval:
            return fval["stringValue"]
        if "timestampValue" in fval:
            return fval["timestampValue"]
        if "arrayValue" in fval:
            vals = fval["arrayValue"].get("values", [])
            return [self._firestore_to_python_value(v) for v in vals]
        if "mapValue" in fval:
            fields = fval["mapValue"].get("fields", {})
            return {k: self._firestore_to_python_value(v) for k, v in fields.items()}
        return None

    # --- Chat Sessions in Cloud Firestore ---
    def save_session(self, session_id: str, employee_id: str, history: List[Dict[str, Any]]) -> bool:
        """
        Saves chat history and metadata directly to Cloud Firestore collection 'sessions'.
        """
        doc_data = {
            "session_id": session_id,
            "employee_id": employee_id,
            "history": history,
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }
        fields = {k: self._python_to_firestore_value(v) for k, v in doc_data.items()}
        payload = json.dumps({"fields": fields}).encode("utf-8")
        resp = self._execute_request(f"sessions/{session_id}", method="PATCH", payload=payload)
        return resp is not None

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves chat history and session data directly from Cloud Firestore collection 'sessions'.
        """
        res = self._execute_request(f"sessions/{session_id}", method="GET")
        if res and "fields" in res:
            return {k: self._firestore_to_python_value(v) for k, v in res["fields"].items()}
        return None

    # --- Checklists & Onboarding Tasks in Cloud Firestore ---
    def get_completed_tasks(self, employee_id: str) -> List[str]:
        """
        Retrieves completed onboarding task IDs directly from Cloud Firestore collection 'checklists'.
        """
        res = self._execute_request(f"checklists/{employee_id}", method="GET")
        if res and "fields" in res:
            parsed = {k: self._firestore_to_python_value(v) for k, v in res["fields"].items()}
            return parsed.get("tasks", [])
        return []

    def mark_task_completed(self, employee_id: str, task_id: str) -> None:
        """
        Adds a completed task ID to Cloud Firestore collection 'checklists/{employee_id}'.
        """
        tasks = list(self.get_completed_tasks(employee_id))
        if task_id not in tasks:
            tasks.append(task_id)

        doc_data = {
            "employee_id": employee_id,
            "tasks": tasks,
            "completed_count": len(tasks),
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }
        fields = {k: self._python_to_firestore_value(v) for k, v in doc_data.items()}
        payload = json.dumps({"fields": fields}).encode("utf-8")
        self._execute_request(f"checklists/{employee_id}", method="PATCH", payload=payload)

    def is_task_completed(self, employee_id: str, task_id: str) -> bool:
        return task_id in self.get_completed_tasks(employee_id)

    # --- Timesheets in Cloud Firestore ---
    def save_timesheet(self, employee_id: str, hours: float, notes: str, salesforce_id: str = "") -> Dict[str, Any]:
        """
        Saves weekly timesheet submission directly to Cloud Firestore collection 'timesheets/{employee_id}'.
        """
        doc_data = {
            "timesheet_id": f"ts_{employee_id}",
            "employee_id": employee_id,
            "hours": hours,
            "notes": notes,
            "status": "SUBMITTED",
            "submitted": True,
            "salesforce_id": salesforce_id,
            "submitted_at": datetime.utcnow().isoformat() + "Z"
        }
        fields = {k: self._python_to_firestore_value(v) for k, v in doc_data.items()}
        payload = json.dumps({"fields": fields}).encode("utf-8")
        self._execute_request(f"timesheets/{employee_id}", method="PATCH", payload=payload)
        return doc_data

    def get_timesheet(self, employee_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves timesheet directly from Cloud Firestore collection 'timesheets/{employee_id}'.
        """
        res = self._execute_request(f"timesheets/{employee_id}", method="GET")
        if res and "fields" in res:
            return {k: self._firestore_to_python_value(v) for k, v in res["fields"].items()}
        return None

    # --- Incidents in Cloud Firestore ---
    def add_incident(self, incident: Dict[str, Any]) -> None:
        """
        Saves an incident ticket directly to Cloud Firestore collection 'incidents/{incident_id}'.
        """
        inc_id = incident.get("incident_id") or f"inc_{int(datetime.utcnow().timestamp() * 1000)}"
        incident["incident_id"] = inc_id
        if "created_at" not in incident:
            incident["created_at"] = datetime.utcnow().isoformat() + "Z"

        fields = {k: self._python_to_firestore_value(v) for k, v in incident.items()}
        payload = json.dumps({"fields": fields}).encode("utf-8")
        self._execute_request(f"incidents/{inc_id}", method="PATCH", payload=payload)

    def get_all_incidents(self) -> List[Dict[str, Any]]:
        """
        Retrieves all incident tickets directly from Cloud Firestore collection 'incidents'.
        """
        res = self._execute_request("incidents", method="GET")
        if res and "documents" in res:
            result = []
            for doc in res["documents"]:
                fields = doc.get("fields", {})
                parsed = {k: self._firestore_to_python_value(v) for k, v in fields.items()}
                result.append(parsed)
            return result
        return []

    # --- Employee Operational Profile in Cloud Firestore ---
    def save_employee(self, employee_data: Dict[str, Any]) -> None:
        """
        Saves or updates employee profile in Cloud Firestore collection 'employees/{employee_id}'.
        """
        emp_id = employee_data.get("employee_id")
        if not emp_id:
            return
        clean_id = emp_id.replace(" ", "_")

        store_fields = {
            "employee_id": emp_id,
            "name": employee_data.get("name", ""),
            "email": employee_data.get("email", ""),
            "department": employee_data.get("department", "Engineering"),
            "team": employee_data.get("team", "Payments"),
            "job_role": employee_data.get("job_role", "Engineer"),
            "authorization_role": employee_data.get("authorization_role", "employee"),
            "assigned_buddy_name": employee_data.get("assigned_buddy_name", ""),
            "assigned_buddy_email": employee_data.get("assigned_buddy_email", ""),
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }
        fields = {k: self._python_to_firestore_value(v) for k, v in store_fields.items()}
        payload = json.dumps({"fields": fields}).encode("utf-8")
        self._execute_request(f"employees/{clean_id}", method="PATCH", payload=payload)

    def get_employee(self, employee_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves employee profile from Cloud Firestore collection 'employees/{employee_id}'.
        """
        clean_id = employee_id.replace(" ", "_")
        res = self._execute_request(f"employees/{clean_id}", method="GET")
        if res and "fields" in res:
            return {k: self._firestore_to_python_value(v) for k, v in res["fields"].items()}
        return None

# Singleton instance
firestore_db = FirestoreManager()
