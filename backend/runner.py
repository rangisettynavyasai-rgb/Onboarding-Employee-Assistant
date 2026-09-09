#!/usr/bin/env python3
"""
Company AI Assistant: Python Backend CLI & RPC Dispatcher
Accepts JSON payload on stdin, executes domain services and multi-agent logic in pure Python, returns JSON on stdout.
"""
import sys
import os
import json
from typing import Dict, Any

# Ensure project root is on sys.path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.models import (
    EmployeeRecord, AuthorizationRole, TaskStatus, IncidentSeverity
)
from backend.services import (
    AuthService,
    OnboardingService,
    OperationsService,
    KnowledgeService,
    ProactiveService,
    SessionService,
)
from backend.agents import SupervisorAgent

def main():
    try:
        if len(sys.argv) > 1 and sys.argv[1].strip():
            raw_input = sys.argv[1]
        else:
            raw_input = sys.stdin.read()

        if not raw_input.strip():
            print(json.dumps({"error": "Empty input"}))
            return

        payload = json.loads(raw_input)
        action = payload.get("action")
        identity = payload.get("identity") or payload.get("token") or "EMP-2026-001"

        if action == "health":
            output = {
                "status": "ok",
                "service": "Onboarding-Employee-Assistant-Python-Backend",
                "runtime": "Python 3.10",
            }
            print(json.dumps(output))
            return

        if action == "register_google_profile":
            email = payload.get("email", "")
            name = payload.get("name", "")
            sub = payload.get("sub", "")
            picture = payload.get("picture", "")
            emp = AuthService.register_google_profile(email, name, sub, picture)
            print(json.dumps(emp.to_dict()))
            return

        if action == "list_employees":
            from backend.bigquery_service import BigQueryService
            employees = BigQueryService.get_all_employees()
            print(json.dumps({"employees": employees}))
            return

        if action == "check_secrets":
            from backend.config import check_secrets_status
            print(json.dumps({"secrets": check_secrets_status()}))
            return

        employee = AuthService.resolve_employee(identity)
        if not employee:
            print(json.dumps({"error": "Unauthorized: Unable to resolve employee identity"}))
            return
        elif action == "resolve_employee" or action == "login":
            password = payload.get("password")
            if action == "login" and password is not None:
                auth_emp = AuthService.authenticate_credentials(identity, password)
                if not auth_emp:
                    print(json.dumps({"error": "Invalid corporate credentials or password"}))
                    return
                employee = auth_emp
            output = {
                "status": "authenticated",
                "employee": employee.to_dict()
            }
        elif action == "landing":
            output = ProactiveService.generate_landing(employee)
        elif action == "chat":
            message = payload.get("message", "")
            effective_sess_id = payload.get("session_id") or f"sess-{employee.employee_id.lower()}"
            
            # Record user turn in persistent session
            if message:
                SessionService.append_message(effective_sess_id, employee.employee_id, "user", message)

            result = SupervisorAgent.route(employee, message)
            resp_text = result.get("response", "")
            agent_name = result.get("agent", "Supervisor Agent")
            suggested = result.get("suggested_actions", [])

            # Record assistant turn in persistent session
            if resp_text:
                SessionService.append_message(effective_sess_id, employee.employee_id, "assistant", resp_text, agent_name)

            output = {
                "response": resp_text,
                "agent_invoked": agent_name,
                "suggested_actions": suggested,
                "session_id": effective_sess_id,
                "employee_id": employee.employee_id,
            }
        elif action == "get_checklist":
            output = OnboardingService.get_checklist(employee.employee_id)
        elif action == "complete_task":
            task_id = payload.get("task_id", "")
            success = OnboardingService.complete_task(employee.employee_id, task_id)
            output = {
                "success": success,
                "checklist": OnboardingService.get_checklist(employee.employee_id)
            }
        elif action == "team_progress":
            output = OnboardingService.get_team_progress(employee)
        elif action == "search_knowledge":
            query = payload.get("query", "")
            chunks = KnowledgeService.search_authorized(employee, query)
            output = {
                "query": query,
                "count": len(chunks),
                "chunks": [c.to_dict() for c in chunks],
                "context": KnowledgeService.format_context(employee, chunks, query)
            }
        elif action == "get_insights":
            insights = KnowledgeService.get_authorized_insights(employee)
            output = {
                "employee_id": employee.employee_id,
                "team": employee.team,
                "clearance": employee.authorization_role.value if isinstance(employee.authorization_role, AuthorizationRole) else employee.authorization_role,
                "total_insights": len(insights),
                "insights": insights,
            }
        elif action == "timesheet_status":
            output = OperationsService.get_timesheet_status(employee.employee_id)
        elif action == "submit_timesheet":
            hours = float(payload.get("hours", 40.0))
            notes = payload.get("notes", "")
            output = OperationsService.submit_timesheet(employee.employee_id, hours, notes)
        elif action == "get_document":
            doc_id = payload.get("doc_id", "")
            doc = KnowledgeService.get_document(employee, doc_id)
            if doc:
                output = doc
            else:
                output = {"error": f"Document {doc_id} not found or restricted"}
        elif action == "get_all_documents":
            output = {
                "documents": KnowledgeService.get_all_documents(employee)
            }
        elif action == "create_incident":
            category = payload.get("category", "Platform / General")
            summary = payload.get("summary", "")
            sev_str = payload.get("severity", "MEDIUM").upper()
            sev = IncidentSeverity[sev_str] if sev_str in IncidentSeverity.__members__ else IncidentSeverity.MEDIUM
            output = OperationsService.create_incident(employee, category, summary, sev)
        elif action == "resolve_escalation":
            domain = payload.get("domain", employee.team)
            output = OperationsService.resolve_escalation(domain)
        elif action in ["get_points_of_contact", "get_contacts", "point_to_person"]:
            access_token = payload.get("access_token")
            output = OperationsService.get_points_of_contact(employee, access_token)
        elif action in ["session_history", "get_session_history"]:
            session_id = payload.get("session_id")
            session = SessionService.get_or_create_session(employee.employee_id, session_id)
            output = session.to_dict()
        elif action == "record_chat_turn":
            session_id = payload.get("session_id") or f"sess-{employee.employee_id.lower()}"
            user_msg = payload.get("user_message", "")
            asst_msg = payload.get("assistant_message", "")
            agent = payload.get("agent", "Company AI Assistant (Gemini 3.6)")
            if user_msg:
                SessionService.append_message(session_id, employee.employee_id, "user", user_msg)
            if asst_msg:
                SessionService.append_message(session_id, employee.employee_id, "assistant", asst_msg, agent)
            session = SessionService.get_or_create_session(employee.employee_id, session_id)
            output = {"success": True, "session": session.to_dict()}
        elif action == "register_google_profile":
            email = payload.get("email", "")
            name = payload.get("name", "")
            sub = payload.get("sub", "")
            picture = payload.get("picture", "")
            emp = AuthService.register_google_profile(email, name, sub, picture)
            output = emp.to_dict()
        elif action == "calendar_ooo":
            access_token = payload.get("access_token")
            from backend.calendar_service import CalendarService
            output = CalendarService.get_out_of_office_status(access_token)
        elif action in ["integration_status", "test_connections"]:
            from backend.jira_service import JiraService
            from backend.salesforce_service import SalesforceService
            from backend.calendar_service import CalendarService
            from backend.firestore import firestore_db
            from backend.bigquery_service import BigQueryService
            from backend.gcs_service import GCSService
            from backend.config import get_secret_ids
            access_token = payload.get("access_token")
            output = {
                "firestore": firestore_db.test_connection(),
                "bigquery": BigQueryService.test_connection(),
                "gcs": GCSService.test_connection(),
                "jira": {
                    "site_url": JiraService.get_site_url(),
                    "configured": JiraService.is_configured(),
                    "project_key": JiraService.PROJECT_KEY,
                },
                "salesforce": {
                    "instance_url": SalesforceService.get_instance_url(),
                    "configured": SalesforceService.is_configured(),
                },
                "calendar": CalendarService.get_out_of_office_status(access_token),
                "secrets": {
                    env_var: {
                        "secret_id": sec_id,
                        "configured": bool(os.environ.get(env_var, "").strip()),
                    }
                    for env_var, sec_id in get_secret_ids().items()
                },
            }
        else:
            output = {"error": f"Unknown action: {action}"}

        print(json.dumps(output))

    except Exception as e:
        import traceback
        print(json.dumps({"error": str(e), "traceback": traceback.format_exc()}))

if __name__ == "__main__":
    main()

