#!/usr/bin/env python3
"""
Patchamomma 2026: Multi-Agent Subsystem in Python
Implements:
  - Supervisor Orchestrator with intent triage
  - Onboarding Guide Agent (tracks tasks, due dates, buddy connects)
  - Code & Architecture Mentor Agent
  - Knowledge Mesh Agent with Pre-Retrieval ACL evaluation
  - Operations & HR Policy Agent
"""
import os
import re
from typing import Dict, Any, List
from backend.models import EmployeeRecord, TaskStatus
from backend.auth_policy import AuthPolicy
from backend.data import ONBOARDING_TASKS, KNOWLEDGE_CATALOG, EMPLOYEES

class KnowledgeMeshAgent:
    @staticmethod
    def search(employee: EmployeeRecord, query: str) -> Dict[str, Any]:
        q = query.lower()
        allowed_assets = AuthPolicy.filter_knowledge_assets(employee, KNOWLEDGE_CATALOG)
        
        results = []
        words = [w for w in re.split(r'\W+', q) if len(w) > 2]

        for asset in allowed_assets:
            matched = False
            for chunk in asset.chunks:
                text = (asset.title + " " + chunk.content + " " + (asset.description or "")).lower()
                if q in text or any(w in text for w in words):
                    results.append({
                        "doc_id": asset.document_id,
                        "title": asset.title,
                        "team": asset.team,
                        "access_level": asset.access_level,
                        "content": chunk.content,
                    })
                    matched = True
                    break

        if not results:
            return {
                "agent": "Knowledge Mesh Agent",
                "response": (
                    f"🔍 **Knowledge Mesh Search**\n\n"
                    f"No authorized internal documentation found matching \"{query}\".\n\n"
                    f"*Note*: Access to managerial documents is restricted to Managers and HR. "
                    f"Team-specific runbooks are scoped to your team ({employee.team}) and company-wide policies."
                ),
                "suggested_actions": ["Coding Standards", "View Pending Tasks"],
            }

        response_lines = [
            f"📚 **Knowledge Mesh Results (Authorized Pre-Retrieval Filter)**\n",
            f"Security Clearance: `{employee.authorization_role.value if hasattr(employee.authorization_role, 'value') else employee.authorization_role}` | Team: `{employee.team}`\n"
        ]
        for r in results:
            response_lines.append(f"### 📄 {r['doc_id']} (Domain: {r['team']})")
            response_lines.append(r['content'])
            response_lines.append("")

        return {
            "agent": "Knowledge Mesh Agent",
            "response": "\n".join(response_lines),
            "suggested_actions": ["Coding Standards", "Check Timesheet"],
        }

class OnboardingAgent:
    @staticmethod
    def handle(employee: EmployeeRecord, query: str) -> Dict[str, Any]:
        tasks = ONBOARDING_TASKS.get(employee.employee_id, [])
        for t in tasks:
            t.calculate_due(employee.joining_date)

        completed = [t for t in tasks if t.status == TaskStatus.COMPLETED]
        pending = [t for t in tasks if t.status != TaskStatus.COMPLETED]
        overdue = [t for t in pending if t.is_overdue]

        lines = [
            f"📋 **Onboarding Journey Status for {employee.name}**\n",
            f"Track: `{employee.onboarding_track}` | Progress: **{len(completed)}/{len(tasks)} Completed**\n"
        ]

        if overdue:
            lines.append(f"⚠️ **Attention: You have {len(overdue)} overdue onboarding task(s):**")
            for t in overdue:
                lines.append(f"- 🔴 **{t.title}** (Due: {t.due_date}) - `{t.task_id}`")
            lines.append("")

        if pending:
            next_t = pending[0]
            lines.append(f"👉 **Next Up:** {next_t.title}")
            lines.append(f"Description: {next_t.description}")
            lines.append(f"Due Date: {next_t.due_date}")

        if employee.assigned_buddy_name:
            lines.append(f"\n🤝 **Assigned Onboarding Buddy:** {employee.assigned_buddy_name} ({employee.assigned_buddy_email})")

        return {
            "agent": "Onboarding Guide Agent",
            "response": "\n".join(lines),
            "suggested_actions": ["Complete Security Module", "Connect with Buddy", "View Runbooks"],
        }

class CodeMentorAgent:
    @staticmethod
    def handle(employee: EmployeeRecord, query: str) -> Dict[str, Any]:
        return {
            "agent": "Code Mentor Agent",
            "response": (
                "💻 **Corporate Coding & Logging Standards 2026**\n\n"
                "1. **Zero Raw Print Policy**: Never commit raw `print(...)` or `console.log(...)` statements. "
                "All services must emit structured JSON logs with correlation IDs:\n"
                "```python\n"
                "logger.info('PAYMENT_PROCESSED', extra={'user_id': employee_id, 'status': 'SUCCESS'})\n"
                "```\n"
                "2. **Cloud SQL Proxy**: Connect via 127.0.0.1:5432 using IAM database authentication, never hardcoded credentials.\n"
                "3. **Idempotency**: All mutative endpoints require an `Idempotency-Key` HTTP header with a 24-hour Redis TTL cache."
            ),
            "suggested_actions": ["Search Runbooks", "View Pending Tasks"],
        }

class OpsAgent:
    @staticmethod
    def handle(employee: EmployeeRecord, query: str) -> Dict[str, Any]:
        return {
            "agent": "Operations & HR Policy Agent",
            "response": (
                "⏱️ **Patchamomma People & Operations Notice**\n\n"
                "• **Core Working Hours**: 10:00 AM – 4:00 PM local time.\n"
                "• **Weekly Timesheet**: Due every Friday by 5:00 PM to ensure automated payroll processing.\n"
                "• **IT Support**: Use the 'Report IT Ticket' quick action in the dashboard to submit high-priority hardware or access requests directly to the Service Desk."
            ),
            "suggested_actions": ["Check Timesheet Status", "Report IT Incident"],
        }

class SupervisorAgent:
    @staticmethod
    def route(employee: EmployeeRecord, message: str) -> Dict[str, Any]:
        lower = message.lower()
        if any(w in lower for w in ["onboard", "task", "checklist", "buddy", "status", "progress", "overdue"]):
            return OnboardingAgent.handle(employee, message)
        elif any(w in lower for w in ["log", "code", "python", "typescript", "standards", "sql", "idempotent", "git"]):
            return CodeMentorAgent.handle(employee, message)
        elif any(w in lower for w in ["timesheet", "hour", "vacation", "policy", "it ticket", "payroll"]):
            return OpsAgent.handle(employee, message)
        else:
            # Default to Knowledge Mesh ACL pre-retrieval search
            return KnowledgeMeshAgent.search(employee, message)
