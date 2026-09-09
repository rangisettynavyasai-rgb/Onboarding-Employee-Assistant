#!/usr/bin/env python3
"""
Company AI Assistant: Enterprise Python Cloud Firestore Persistence Layer
Direct integration with Google Cloud Firestore database using the official Google Cloud SDK.
ai-studio-onboardingemploy-b1158660-8824-4e90-b842-3a0f086d1796
All data is read and written directly to the Cloud Firestore database natively.
"""

import os
import sys
from typing import Dict, Any, Optional, List
from datetime import datetime
from backend.config import get_config_val
from google.cloud import firestore

class FirestoreManager:
    """
    Manages persistent Cloud Firestore read/write operations for employee sessions,
    chat histories, checklists, timesheets, and support incidents directly via the native SDK.
    """

    def __init__(self):
        self.project_id = get_config_val("GCP_PROJECT_ID", "patchamomma-505416")
        self.database_id = get_config_val("FIRESTORE_DATABASE_ID", "onboarding-employee-assistant-firestore-database")

    def _get_client(self) -> firestore.Client:
        """
        Natively instantiates the official Firestore Client.
        Automatically inherits service account credentials or local Application Default Credentials (ADC).
        """
        return firestore.Client(project=self.project_id, database=self.database_id)

    def test_connection(self) -> Dict[str, Any]:
        """
        Tests the live connection to Cloud Firestore and reports collection presence metrics.
        """
        result: Dict[str, Any] = {
            "project_id": self.project_id,
            "database_id": self.database_id,
            "connected": False,
            "collections": {},
            "status": "Checking..."
        }
        try:
            db = self._get_client()
            # Safely stream a single document to check read validation parameters
            chk_docs = list(db.collection("checklists").limit(1).stream())
            sess_docs = list(db.collection("sessions").limit(1).stream())
            
            result["connected"] = True
            result["status"] = "Connected successfully to Cloud Firestore via Native SDK Client"
            result["collections"]["checklists"] = len(chk_docs)
            result["collections"]["sessions"] = len(sess_docs)
        except Exception as e:
            result["status"] = f"SDK Firestore Connection failed: {str(e)}"

        return result

    # --- Chat Sessions in Cloud Firestore ---
    def save_session(self, session_id: str, employee_id: str, history: List[Dict[str, Any]]) -> bool:
        """
        Saves chat history and metadata directly to Cloud Firestore collection 'sessions'.
        """
        try:
            db = self._get_client()
            doc_ref = db.collection("sessions").document(session_id)
            doc_data = {
                "session_id": session_id,
                "employee_id": employee_id,
                "history": history,
                "updated_at": datetime.utcnow()
            }
            doc_ref.set(doc_data, merge=True)
            return True
        except Exception as e:
            print(f"[Firestore] save_session error: {e}", file=sys.stderr)
            return False

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves chat history and session data directly from Cloud Firestore collection 'sessions'.
        """
        try:
            db = self._get_client()
            doc = db.collection("sessions").document(session_id).get()
            if doc.exists:
                data = doc.to_dict() or {}
                if "updated_at" in data and isinstance(data["updated_at"], datetime):
                    data["updated_at"] = data["updated_at"].isoformat() + "Z"
                return data
        except Exception as e:
            print(f"[Firestore] get_session error: {e}", file=sys.stderr)
        return None
    # --- Checklists & Onboarding Tasks in Cloud Firestore ---
    def get_completed_tasks(self, employee_id: str) -> List[str]:
        """
        Retrieves completed onboarding task IDs directly from Cloud Firestore collection 'checklists'.
        """
        try:
            db = self._get_client()
            doc = db.collection("checklists").document(employee_id).get()
            if doc.exists:
                data = doc.to_dict() or {}
                return data.get("tasks", [])
        except Exception as e:
            print(f"[Firestore] get_completed_tasks error: {e}", file=sys.stderr)
        return []

    def mark_task_completed(self, employee_id: str, task_id: str) -> None:
        """
        Adds a completed task ID to Cloud Firestore collection 'checklists/{employee_id}'.
        """
        try:
            db = self._get_client()
            doc_ref = db.collection("checklists").document(employee_id)
            
            # Fetch existing tasks to append safely
            tasks = list(self.get_completed_tasks(employee_id))
            if task_id not in tasks:
                tasks.append(task_id)

            doc_data = {
                "employee_id": employee_id,
                "tasks": tasks,
                "completed_count": len(tasks),
                "updated_at": datetime.utcnow()
            }
            doc_ref.set(doc_data, merge=True)
        except Exception as e:
            print(f"[Firestore] mark_task_completed error: {e}", file=sys.stderr)

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
            "submitted_at": datetime.utcnow()
        }
        try:
            db = self._get_client()
            db.collection("timesheets").document(employee_id).set(doc_data, merge=True)
        except Exception as e:
            print(f"[Firestore] save_timesheet error: {e}", file=sys.stderr)
            
        # Coerce time back to pipeline ISO formats for app serialization
        return {
            **doc_data,
            "submitted_at": doc_data["submitted_at"].isoformat() + "Z"
        }

    def get_timesheet(self, employee_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves timesheet directly from Cloud Firestore collection 'timesheets/{employee_id}'.
        """
        try:
            db = self._get_client()
            doc = db.collection("timesheets").document(employee_id).get()
            if doc.exists:
                data = doc.to_dict() or {}
                if "submitted_at" in data and isinstance(data["submitted_at"], datetime):
                    data["submitted_at"] = data["submitted_at"].isoformat() + "Z"
                return data
        except Exception as e:
            print(f"[Firestore] get_timesheet error: {e}", file=sys.stderr)
        return None
    # --- Incidents in Cloud Firestore ---
    def add_incident(self, incident: Dict[str, Any]) -> None:
        """
        Saves an incident ticket directly to Cloud Firestore collection 'incidents/{incident_id}'.
        """
        inc_id = incident.get("incident_id") or f"inc_{int(datetime.utcnow().timestamp() * 1000)}"
        incident["incident_id"] = inc_id
        if "created_at" not in incident:
            incident["created_at"] = datetime.utcnow()
        elif isinstance(incident["created_at"], str):
            try:
                # Normalize pipeline string timestamps to standard datetime objects
                clean_ts = incident["created_at"].replace("Z", "+00:00")
                incident["created_at"] = datetime.fromisoformat(clean_ts)
            except Exception:
                incident["created_at"] = datetime.utcnow()

        try:
            db = self._get_client()
            db.collection("incidents").document(inc_id).set(incident, merge=True)
        except Exception as e:
            print(f"[Firestore] add_incident error: {e}", file=sys.stderr)

    def get_all_incidents(self) -> List[Dict[str, Any]]:
        """
        Retrieves all incident tickets directly from Cloud Firestore collection 'incidents'.
        """
        result = []
        try:
            db = self._get_client()
            docs = db.collection("incidents").order_by("created_at", direction=firestore.Query.DESCENDING).stream()
            for doc in docs:
                data = doc.to_dict() or {}
                if "created_at" in data and isinstance(data["created_at"], datetime):
                    data["created_at"] = data["created_at"].isoformat() + "Z"
                result.append(data)
        except Exception as e:
            print(f"[Firestore] get_all_incidents error: {e}", file=sys.stderr)
        return result

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
            "updated_at": datetime.utcnow(),
        }
        try:
            db = self._get_client()
            db.collection("employees").document(clean_id).set(store_fields, merge=True)
        except Exception as e:
            print(f"[Firestore] save_employee error: {e}", file=sys.stderr)

    def get_employee(self, employee_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves employee profile from Cloud Firestore collection 'employees/{employee_id}'.
        """
        clean_id = employee_id.replace(" ", "_").replace("@", "_").replace(".", "_")
        try:
            db = self._get_client()
            doc = db.collection("employees").document(clean_id).get()
            if doc.exists:
                data = doc.to_dict() or {}
                if "updated_at" in data and isinstance(data["updated_at"], datetime):
                    data["updated_at"] = data["updated_at"].isoformat() + "Z"
                return data
        except Exception as e:
            print(f"[Firestore] get_employee error: {e}", file=sys.stderr)
        return None

    def lookup_employee_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Looks up an employee document from Cloud Firestore collection 'employees' filtered by email.
        """
        if not email:
            return None
        clean_email = email.strip().lower()
        
        try:
            db = self._get_client()
            # Execute structured server-side query filters using native client streams
            docs = db.collection("employees").where(filter=firestore.FieldFilter("email", "==", clean_email)).limit(1).stream()
            for doc in docs:
                data = doc.to_dict() or {}
                if "updated_at" in data and isinstance(data["updated_at"], datetime):
                    data["updated_at"] = data["updated_at"].isoformat() + "Z"
                return data
        except Exception as err:
            print(f"[Firestore] lookup_employee_by_email error: {err}", file=sys.stderr)
        return None

# Singleton instance matching your application references
firestore_db = FirestoreManager()
