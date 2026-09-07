#!/usr/bin/env python3
"""
Patchamomma 2026: Python Backend CLI & RPC Dispatcher
Accepts JSON payload on stdin, runs authorization & agent logic in pure Python, returns JSON on stdout.
"""
import sys
import json
from typing import Dict, Any

from backend.models import (
    EmployeeRecord, AuthorizationRole, TaskStatus
)
from backend.data import EMPLOYEES, ONBOARDING_TASKS, KNOWLEDGE_CATALOG
from backend.auth_policy import AuthPolicy
from backend.agents import SupervisorAgent

def resolve_employee(identity: str) -> EmployeeRecord:
    clean = identity.replace("Bearer ", "").strip()
    
    # 1. Match employee_id
    if clean in EMPLOYEES:
        return EMPLOYEES[clean]
    
    # 2. Match email
    for emp in EMPLOYEES.values():
        if emp.email.lower() == clean.lower():
            return emp
            
    # 3. Direct mock token
    token_map = {
        "mock-google-token-rahul": "EMP-2026-001",
        "mock-google-token-maya": "EMP-2026-002",
        "mock-google-token-amanda": "EMP-2026-009",
        "mock-google-token-sarah": "EMP-2026-010",
    }
    if clean in token_map:
        return EMPLOYEES[token_map[clean]]

    # 4. Fallback or new corporate email provisioning
    if "@" in clean:
        emp_id = f"EMP-{abs(hash(clean)) % 1000000:06d}"
        prefix = clean.split("@")[0]
        name = prefix.replace(".", " ").title()
        new_emp = EmployeeRecord(
            employee_id=emp_id,
            google_subject=f"sub-{clean}",
            email=clean,
            name=name,
            department="Engineering",
            team="Payments",
            job_role="Software Engineer",
            authorization_role=AuthorizationRole.EMPLOYEE,
            manager_id="EMP-2026-010",
            location="San Francisco, CA",
            joining_date="2026-09-01",
            onboarding_status="IN_PROGRESS",
            is_day_one=False,
            assigned_buddy_name="Priya Nair",
            assigned_buddy_email="priya.nair@company.com",
            onboarding_track="Backend"
        )
        EMPLOYEES[emp_id] = new_emp
        return new_emp

    # Default fallback
    return EMPLOYEES["EMP-2026-001"]

def get_checklist_for_employee(employee: EmployeeRecord) -> Dict[str, Any]:
    tasks = ONBOARDING_TASKS.get(employee.employee_id)
    if not tasks:
        # Default starter tasks
        tasks = [
            ONBOARDING_TASKS["EMP-2026-001"][0],
            ONBOARDING_TASKS["EMP-2026-001"][1],
        ]
        ONBOARDING_TASKS[employee.employee_id] = tasks

    # Calculate due dates and overdue statuses relative to joining_date and current time (2026-09-07)
    for t in tasks:
        t.calculate_due(employee.joining_date)

    completed_count = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
    pending_tasks = [t for t in tasks if t.status != TaskStatus.COMPLETED]
    next_task = pending_tasks[0].to_dict() if pending_tasks else None

    return {
        "employee_id": employee.employee_id,
        "track": employee.onboarding_track,
        "tasks": [t.to_dict() for t in tasks],
        "completed_count": completed_count,
        "total_count": len(tasks),
        "next_pending_task": next_task,
    }

def complete_task(employee: EmployeeRecord, task_id: str) -> Dict[str, Any]:
    tasks = ONBOARDING_TASKS.get(employee.employee_id, [])
    found = False
    for t in tasks:
        if t.task_id == task_id:
            t.status = TaskStatus.COMPLETED
            t.completed_at = "2026-09-07T11:00:00Z"
            t.is_overdue = False
            found = True
            break
    return {
        "success": found,
        "checklist": get_checklist_for_employee(employee)
    }

def main():
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            print(json.dumps({"error": "Empty input"}))
            return

        payload = json.loads(raw_input)
        action = payload.get("action")
        identity = payload.get("identity") or payload.get("token") or "EMP-2026-001"

        employee = resolve_employee(identity)

        if action == "resolve_employee":
            output = {
                "status": "authenticated",
                "employee": employee.to_dict()
            }
        elif action == "chat":
            message = payload.get("message", "")
            result = SupervisorAgent.route(employee, message)
            output = {
                "response": result["response"],
                "agent_invoked": result["agent"],
                "suggested_actions": result.get("suggested_actions", []),
                "employee_id": employee.employee_id,
            }
        elif action == "get_checklist":
            output = get_checklist_for_employee(employee)
        elif action == "complete_task":
            task_id = payload.get("task_id", "")
            output = complete_task(employee, task_id)
        elif action == "search_knowledge":
            query = payload.get("query", "")
            result = SupervisorAgent.route(employee, query)
            output = result
        else:
            output = {"error": f"Unknown action: {action}"}

        print(json.dumps(output))

    except Exception as e:
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    main()
