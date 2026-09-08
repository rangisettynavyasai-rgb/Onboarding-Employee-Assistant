#!/usr/bin/env python3
"""
Enterprise State Store: Persists task completion, timesheets, and tickets across CLI/server invocations
directly to Google Cloud Firestore (database: ai-studio-onboardingemploy-b1158660-8824-4e90-b842-3a0f086d1796).
No local file storage or persisted_state.json is used.
"""
from typing import Dict, Any, List, Optional
from backend.firestore import firestore_db

def mark_task_completed(employee_id: str, task_id: str) -> None:
    firestore_db.mark_task_completed(employee_id, task_id)

def is_task_completed(employee_id: str, task_id: str) -> bool:
    return firestore_db.is_task_completed(employee_id, task_id)

def get_completed_task_ids(employee_id: str) -> List[str]:
    return firestore_db.get_completed_tasks(employee_id)

def save_timesheet_submission(employee_id: str, hours: float, notes: str, salesforce_id: str = "") -> Dict[str, Any]:
    return firestore_db.save_timesheet(employee_id, hours, notes, salesforce_id)

def get_timesheet_override(employee_id: str) -> Optional[Dict[str, Any]]:
    return firestore_db.get_timesheet(employee_id)

def add_incident(incident: Dict[str, Any]) -> None:
    firestore_db.add_incident(incident)

def get_all_incidents() -> List[Dict[str, Any]]:
    return firestore_db.get_all_incidents()

def save_employee(employee_dict: Dict[str, Any]) -> None:
    firestore_db.save_employee(employee_dict)

def get_employee(employee_id: str) -> Optional[Dict[str, Any]]:
    return firestore_db.get_employee(employee_id)

