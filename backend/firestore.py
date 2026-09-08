#!/usr/bin/env python3
"""
Company AI Assistant: Enterprise Python Firestore Persistence Layer
Direct integration with Google Cloud Firestore database:
ai-studio-onboardingemploy-b1158660-8824-4e90-b842-3a0f086d1796
"""

import json
import os
import urllib.request
import urllib.parse
from typing import Dict, Any, Optional, List
from datetime import datetime

class FirestoreManager:
    """
    Manages persistent Firestore read/write operations for employee sessions,
    chat histories, and task statuses via the Firestore REST API and in-memory fallback.
    """

    def __init__(self):
        self.state_file = os.path.join(os.getcwd(), ".app_state.json")
        self.project_id = os.environ.get("FIREBASE_PROJECT_ID", "")
        self.database_id = os.environ.get("FIRESTORE_DATABASE_ID", "ai-studio-onboardingemploy-b1158660-8824-4e90-b842-3a0f086d1796")
        self.api_key = os.environ.get("FIREBASE_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
        self._memory_sessions: Dict[str, Dict[str, Any]] = {}
        self._memory_tasks: Dict[str, List[str]] = {}
        self._load_config()
        self._load_local_state()

    def _load_local_state(self) -> None:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        if "tasks" in data and isinstance(data["tasks"], dict):
                            self._memory_tasks = data["tasks"]
                        if "sessions" in data and isinstance(data["sessions"], dict):
                            self._memory_sessions = data["sessions"]
            except Exception as e:
                print(f"[StateStore] Notice loading local state: {e}")

    def _save_local_state(self) -> None:
        try:
            temp_file = f"{self.state_file}.tmp"
            data = {
                "tasks": self._memory_tasks,
                "sessions": self._memory_sessions,
                "updated_at": datetime.utcnow().isoformat() + "Z",
            }
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(temp_file, self.state_file)
        except Exception as e:
            print(f"[StateStore] Warning saving local state: {e}")

    def _load_config(self) -> None:
        app_cfg_path = os.path.join(os.getcwd(), "app.config.json")
        if os.path.exists(app_cfg_path):
            try:
                with open(app_cfg_path, "r", encoding="utf-8") as f:
                    app_cfg = json.load(f)
                    self.project_id = os.environ.get("GCP_PROJECT_ID") or os.environ.get("FIREBASE_PROJECT_ID") or app_cfg.get("gcpProjectId", self.project_id)
                    self.database_id = os.environ.get("FIRESTORE_DATABASE_ID") or app_cfg.get("firestoreDatabaseId", self.database_id)
                    self.api_key = os.environ.get("FIREBASE_API_KEY", self.api_key)
            except Exception as e:
                print(f"[Firestore] Notice: could not parse {app_cfg_path}: {e}")

    @property
    def base_url(self) -> str:
        return (
            f"https://firestore.googleapis.com/v1/projects/{self.project_id}/"
            f"databases/{self.database_id}/documents"
        )

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

    def save_session(self, session_id: str, employee_id: str, history: List[Dict[str, Any]]) -> bool:
        """
        Saves chat history and metadata to Firestore collection 'sessions' and local state.
        """
        self._load_local_state()
        doc_data = {
            "session_id": session_id,
            "employee_id": employee_id,
            "history": history,
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }
        self._memory_sessions[session_id] = doc_data
        self._save_local_state()

        if not self.api_key:
            return True

        url = f"{self.base_url}/sessions/{session_id}?key={self.api_key}"
        fields = {k: self._python_to_firestore_value(v) for k, v in doc_data.items()}
        payload = json.dumps({"fields": fields}).encode("utf-8")

        req = urllib.request.Request(url, data=payload, method="PATCH", headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status in (200, 201)
        except Exception:
            return True

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves chat history and session data from Firestore or cache.
        """
        self._load_local_state()
        if not self.api_key:
            return self._memory_sessions.get(session_id)

        url = f"{self.base_url}/sessions/{session_id}?key={self.api_key}"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                fields = data.get("fields", {})
                res = {k: self._firestore_to_python_value(v) for k, v in fields.items()}
                self._memory_sessions[session_id] = res
                self._save_local_state()
                return res
        except Exception:
            return self._memory_sessions.get(session_id)

    # --- Checklists Persistence ---
    def get_completed_tasks(self, employee_id: str) -> List[str]:
        self._load_local_state()
        cache_key = f"chk_{employee_id}"
        if cache_key in self._memory_tasks:
            return self._memory_tasks[cache_key]

        if not self.api_key:
            return self._memory_tasks.get(cache_key, [])

        url = f"{self.base_url}/checklists/{employee_id}?key={self.api_key}"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                fields = data.get("fields", {})
                parsed = {k: self._firestore_to_python_value(v) for k, v in fields.items()}
                tasks = parsed.get("tasks", [])
                self._memory_tasks[cache_key] = tasks
                self._save_local_state()
                return tasks
        except Exception:
            return self._memory_tasks.get(cache_key, [])

    def mark_task_completed(self, employee_id: str, task_id: str) -> None:
        self._load_local_state()
        tasks = list(self.get_completed_tasks(employee_id))
        if task_id not in tasks:
            tasks.append(task_id)
        cache_key = f"chk_{employee_id}"
        self._memory_tasks[cache_key] = tasks
        self._save_local_state()

        if not self.api_key:
            return

        doc_data = {
            "employee_id": employee_id,
            "tasks": tasks,
            "completed_count": len(tasks),
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }
        url = f"{self.base_url}/checklists/{employee_id}?key={self.api_key}"
        fields = {k: self._python_to_firestore_value(v) for k, v in doc_data.items()}
        payload = json.dumps({"fields": fields}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, method="PATCH", headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=3)
        except Exception as e:
            print(f"[Firestore] Notice: Could not update checklist for {employee_id} via remote API: {e}")

    def is_task_completed(self, employee_id: str, task_id: str) -> bool:
        return task_id in self.get_completed_tasks(employee_id)

    # --- Timesheets Persistence ---
    def save_timesheet(self, employee_id: str, hours: float, notes: str, salesforce_id: str = "") -> Dict[str, Any]:
        self._load_local_state()
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
        self._memory_sessions[f"ts_{employee_id}"] = doc_data
        self._save_local_state()

        if not self.api_key:
            return doc_data

        url = f"{self.base_url}/timesheets/{employee_id}?key={self.api_key}"
        fields = {k: self._python_to_firestore_value(v) for k, v in doc_data.items()}
        payload = json.dumps({"fields": fields}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, method="PATCH", headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=3)
        except Exception as e:
            print(f"[Firestore] Notice: Could not save timesheet for {employee_id} via remote API: {e}")

        return doc_data

    def get_timesheet(self, employee_id: str) -> Optional[Dict[str, Any]]:
        self._load_local_state()
        cached = self._memory_sessions.get(f"ts_{employee_id}")
        if cached:
            return cached

        if not self.api_key:
            return None

        url = f"{self.base_url}/timesheets/{employee_id}?key={self.api_key}"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                fields = data.get("fields", {})
                res = {k: self._firestore_to_python_value(v) for k, v in fields.items()}
                self._memory_sessions[f"ts_{employee_id}"] = res
                self._save_local_state()
                return res
        except Exception:
            return None

    # --- Incidents Persistence ---
    def add_incident(self, incident: Dict[str, Any]) -> None:
        self._load_local_state()
        inc_id = incident.get("incident_id") or f"inc_{int(datetime.utcnow().timestamp() * 1000)}"
        incident["incident_id"] = inc_id
        if "created_at" not in incident:
            incident["created_at"] = datetime.utcnow().isoformat() + "Z"

        if "_incidents_list" not in self._memory_sessions or not isinstance(self._memory_sessions["_incidents_list"], list):
            self._memory_sessions["_incidents_list"] = []
        self._memory_sessions["_incidents_list"].append(incident)
        self._save_local_state()

        if not self.api_key:
            return

        url = f"{self.base_url}/incidents/{inc_id}?key={self.api_key}"
        fields = {k: self._python_to_firestore_value(v) for k, v in incident.items()}
        payload = json.dumps({"fields": fields}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, method="PATCH", headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=3)
        except Exception as e:
            print(f"[Firestore] Notice: Could not save incident {inc_id} via remote API: {e}")

    def get_all_incidents(self) -> List[Dict[str, Any]]:
        self._load_local_state()
        cached = self._memory_sessions.get("_incidents_list")
        if cached and isinstance(cached, list):
            return cached

        if not self.api_key:
            return []

        url = f"{self.base_url}/incidents?key={self.api_key}"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                docs = data.get("documents", [])
                result = []
                for doc in docs:
                    fields = doc.get("fields", {})
                    parsed = {k: self._firestore_to_python_value(v) for k, v in fields.items()}
                    result.append(parsed)
                self._memory_sessions["_incidents_list"] = result
                self._save_local_state()
                return result
        except Exception:
            return []

    # --- Employees Persistence ---
    def save_employee(self, employee_data: Dict[str, Any]) -> None:
        self._load_local_state()
        emp_id = employee_data.get("employee_id")
        if not emp_id:
            return
        clean_id = emp_id.replace(" ", "_")
        self._memory_sessions[f"emp_{clean_id}"] = employee_data
        email = employee_data.get("email", "").lower()
        if email:
            self._memory_sessions[f"emp_email_{email}"] = employee_data
        self._save_local_state()

        if not self.api_key:
            return

        url = f"{self.base_url}/employees/{clean_id}?key={self.api_key}"
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
        req = urllib.request.Request(url, data=payload, method="PATCH", headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=3)
        except Exception as e:
            print(f"[Firestore] Notice: Could not save employee {emp_id} via remote API: {e}")

    def get_employee(self, employee_id: str) -> Optional[Dict[str, Any]]:
        self._load_local_state()
        clean_id = employee_id.replace(" ", "_")
        cached = self._memory_sessions.get(f"emp_{clean_id}")
        if cached:
            return cached

        if not self.api_key:
            return None

        url = f"{self.base_url}/employees/{clean_id}?key={self.api_key}"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                fields = data.get("fields", {})
                res = {k: self._firestore_to_python_value(v) for k, v in fields.items()}
                self._memory_sessions[f"emp_{clean_id}"] = res
                self._save_local_state()
                return res
        except Exception:
            return None

    def lookup_employee_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        self._load_local_state()
        clean_email = email.strip().lower()
        cached = self._memory_sessions.get(f"emp_email_{clean_email}")
        if cached:
            return cached
        # Check all cached employees
        for k, v in self._memory_sessions.items():
            if k.startswith("emp_") and isinstance(v, dict):
                if v.get("email", "").lower() == clean_email:
                    return v
        return None


# Global singleton instance
firestore_db = FirestoreManager()
