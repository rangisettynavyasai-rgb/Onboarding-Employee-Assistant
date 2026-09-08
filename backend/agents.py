#!/usr/bin/env python3
"""
Company AI Assistant: Multi-Agent Subsystem in Python
Implements:
  - Supervisor Orchestrator with intent triage
  - Point to Person Agent (connects employees to human buddy, manager, and domain leads)
  - Onboarding Guide Agent (tracks tasks, due dates, buddy connects)
  - Code & Architecture Mentor Agent
  - Knowledge Mesh Agent with Pre-Retrieval ACL evaluation
  - Operations & HR Policy Agent
"""
import os
import re
from typing import Dict, Any, List
from backend.models import EmployeeRecord, TaskStatus, AuthorizationRole
from backend.services import (
    OnboardingService,
    OperationsService,
    KnowledgeService,
    AuthService,
)

class KnowledgeMeshAgent:
    @staticmethod
    def search(employee: EmployeeRecord, query: str) -> Dict[str, Any]:
        chunks = KnowledgeService.search_authorized(employee, query)
        
        if not chunks:
            contacts = OperationsService.get_points_of_contact(employee)
            buddy = contacts.get("buddy", {})
            manager = contacts.get("manager", {})
            return {
                "agent": "Knowledge Mesh Agent",
                "response": (
                    f"🔍 **Knowledge Mesh Search Notice**\n\n"
                    f"No authorized internal runbooks were found matching \"{query}\".\n\n"
                    f"🤝 **Point to Person Connection**:\n"
                    f"When the AI Assistant doesn't have the needed answer, connect directly with our human points of contact:\n\n"
                    f"• **Assigned Buddy**: **{buddy.get('name', 'Priya Nair')}** ({buddy.get('email', 'priya.nair@company.com')})\n"
                    f"  *Role*: {buddy.get('role', 'Tech Lead')} | *Scope*: {buddy.get('scope', 'Codebase walkthroughs & Day-1 guidance')} (Slack: `{buddy.get('channel', '#payments-dev')}`)\n\n"
                    f"• **Reporting Manager**: **{manager.get('name', 'Sarah Jenkins')}** ({manager.get('email', 'sarah.j@company.com')})\n"
                    f"  *Role*: {manager.get('role', 'Engineering Manager')} | *Scope*: {manager.get('scope', 'Approvals, priorities, and 1:1 check-ins')}\n\n"
                    f"• **IT Systems Admin**: **Marcus Vance** (marcus.v@company.com, `#help-it`)\n"
                    f"• **People Operations (HR)**: **Amanda Walker** (amanda.w@company.com, `#people-ops`)\n\n"
                    f"You can also use the **Point of Contact** quick action to view our complete team escalation directory."
                ),
                "suggested_actions": ["Point of Contact", "Connect with Buddy", "Report IT Ticket", "Search Runbooks"],
            }

        response_lines = [
            f"📚 **Knowledge Mesh Results (Pre-Retrieval ACL Enforced)**\n",
            f"Security Clearance: `{employee.authorization_role.value if hasattr(employee.authorization_role, 'value') else employee.authorization_role}` | Team: `{employee.team}`\n"
        ]
        
        seen_docs = set()
        for chunk in chunks:
            if chunk.document_id not in seen_docs:
                seen_docs.add(chunk.document_id)
                response_lines.append(f"### 📄 Asset `{chunk.document_id}` (Domain: {chunk.team} | Access: {chunk.access_level})")
                response_lines.append(chunk.content.strip())
                response_lines.append("")

        return {
            "agent": "Knowledge Mesh Agent",
            "response": "\n".join(response_lines),
            "suggested_actions": ["Coding Standards", "Check Timesheet", "View Pending Tasks"],
        }


class OnboardingAgent:
    @staticmethod
    def handle(employee: EmployeeRecord, query: str) -> Dict[str, Any]:
        lower = query.lower()

        # Manager or HR checking team progress
        if any(w in lower for w in ["team", "direct report", "rollup", "subordinate"]) and (
            employee.authorization_role in [AuthorizationRole.MANAGER, AuthorizationRole.HR, "manager", "hr"]
        ):
            summary = OnboardingService.get_team_progress(employee)
            lines = [
                f"👥 **Manager Team Onboarding Rollup: {summary['team_name']} Team**",
                f"Manager: **{summary['manager_name']}** | Team Members: **{summary['total_team_members']}**",
                f"Overall Onboarding Completion: **{summary['overall_progress_percentage']}%**\n"
            ]
            for m in summary["members"]:
                status_icon = "🟢" if m["progress_percentage"] == 100 else ("🔴" if m["overdue_tasks"] > 0 else "🟡")
                lines.append(
                    f"{status_icon} **{m['name']}** ({m['job_role']}) - {m['progress_percentage']}% "
                    f"({m['completed_tasks']}/{m['total_tasks']} tasks)"
                )
                if m["overdue_tasks"] > 0:
                    lines.append(f"   ⚠️ Overdue tasks: {m['overdue_tasks']}")
                if m["pending_tasks"]:
                    lines.append(f"   Pending: {', '.join(m['pending_tasks'][:2])}")
            return {
                "agent": "Onboarding Guide Agent",
                "response": "\n".join(lines),
                "suggested_actions": ["View My Tasks", "Connect with Buddy", "Company Policies"],
            }

        # Video orientation assistance
        if any(w in lower for w in ["video", "walkthrough", "recording"]):
            return {
                "agent": "Onboarding Guide Agent",
                "response": (
                    f"🎥 **Onboarding Video Orientation & Deep Dive**\n\n"
                    f"Asset URI: `gs://company-knowledge-mesh/videos/onboarding/{employee.onboarding_track.lower()}_deepdive.mp4`\n\n"
                    f"⏱️ **Essential Timestamp Markers**:\n"
                    f"• **Minute 04:15**: Local Development Environment, GCP Credentials & Git Hooks setup.\n"
                    f"• **Minute 18:45**: Cloud SQL Auth Proxy Sidecar & Workload Identity connectivity."
                ),
                "suggested_actions": ["View Pending Tasks", "Coding Standards", "Search Runbooks"],
            }

        cl = OnboardingService.get_checklist(employee.employee_id)
        tasks = cl.get("tasks", []) if cl else []
        completed = [t for t in tasks if t.get("status") == TaskStatus.COMPLETED.value]
        pending = [t for t in tasks if t.get("status") != TaskStatus.COMPLETED.value]
        overdue = [t for t in pending if t.get("is_overdue")]

        lines = [
            f"📋 **Onboarding Journey Status for {employee.name}**\n",
            f"Track: `{employee.onboarding_track}` | Team: `{employee.team}` | Progress: **{len(completed)}/{len(tasks)} Completed**\n"
        ]

        if overdue:
            lines.append(f"⚠️ **Attention: You have {len(overdue)} overdue onboarding task(s):**")
            for t in overdue:
                lines.append(f"- 🔴 **{t.get('title')}** (Due: {t.get('due_date')}) - `{t.get('task_id')}`")
            lines.append("")

        if pending:
            next_t = pending[0]
            lines.append(f"👉 **Next Up:** {next_t.get('title')}")
            lines.append(f"Description: {next_t.get('description')}")
            lines.append(f"Due Date: {next_t.get('due_date')}")

        if employee.assigned_buddy_name:
            lines.append(f"\n🤝 **Assigned Onboarding Buddy:** {employee.assigned_buddy_name} ({employee.assigned_buddy_email})")

        return {
            "agent": "Onboarding Guide Agent",
            "response": "\n".join(lines),
            "suggested_actions": ["Complete Next Task", "Connect with Buddy", "View Runbooks"],
        }


class CodeMentorAgent:
    @staticmethod
    def handle(employee: EmployeeRecord, query: str) -> Dict[str, Any]:
        return {
            "agent": "Code Mentor Agent",
            "response": (
                "💻 **Corporate Coding & Logging Standards 2026**\n\n"
                "1. **Zero Raw Print Policy**: Never commit raw `print(...)` or `console.log(...)` statements. "
                "All microservices must emit structured RFC-5424 JSON logs with trace correlation IDs:\n"
                "```python\n"
                "import logging, json\n"
                "logger = logging.getLogger('service')\n"
                "logger.info(json.dumps({'event': 'PAYMENT_PROCESSED', 'user_id': user_id, 'trace_id': trace_id}))\n"
                "```\n"
                "2. **Cloud SQL Proxy**: Connect via `127.0.0.1:5432` using IAM database authentication, never hardcoded credentials.\n"
                "3. **Idempotency**: All mutative endpoints require an `Idempotency-Key` HTTP header with a 24-hour Redis TTL cache.\n"
                "4. **Git Commit Format**: Use Conventional Commits (`feat(payments): ...`, `fix(auth): ...`). CI gates verify commit linting."
            ),
            "suggested_actions": ["Search Runbooks", "View Pending Tasks", "Check Timesheet"],
        }


class OpsAgent:
    @staticmethod
    def handle(employee: EmployeeRecord, query: str) -> Dict[str, Any]:
        lower = query.lower()

        # Timesheet inquiry
        if any(w in lower for w in ["timesheet", "hour", "log hours", "payroll"]):
            ts = OperationsService.get_timesheet_status(employee.employee_id)
            return {
                "agent": "Operations & HR Policy Agent",
                "response": (
                    f"⏱️ **Timesheet Status for {employee.name}**\n\n"
                    f"• **Period**: {ts['period']}\n"
                    f"• **Status**: **{ts['status']}**\n"
                    f"• **Hours Logged**: {ts['hours_logged']} hrs\n"
                    f"• **Due Date**: {ts['due_date']}\n\n"
                    f"{ts['message']}"
                ),
                "suggested_actions": ["Timesheet Status", "Coding Standards", "View Pending Tasks"],
            }

        # Escalation / who to contact inquiry
        if any(w in lower for w in ["escalat", "lead", "who to contact", "out of office", "ooo", "backup", "contact for"]):
            # Match team or domain
            domain = "Cloud SQL" if "sql" in lower or "database" in lower else (
                "Kubernetes" if "k8s" in lower or "cluster" in lower else (
                    "IAM & Security" if "iam" in lower or "security" in lower or "access" in lower else (
                        "Data Pipelines" if "pipeline" in lower or "data" in lower else employee.team
                    )
                )
            )
            esc = OperationsService.resolve_escalation(domain)
            return {
                "agent": "Operations & HR Policy Agent",
                "response": (
                    f"🚨 **3-Tier Escalation Routing for '{esc['domain']}'**\n\n"
                    f"• **Routing Status**: `{esc['status']}`\n"
                    f"• **Assigned Contact**: **{esc['assigned_contact']}**\n"
                    f"• **Slack Channel**: `{esc['channel']}`\n\n"
                    f"{esc['message']}"
                ),
                "suggested_actions": ["Report IT Ticket", "Search Runbooks", "Check Timesheet"],
            }

        return {
            "agent": "Operations & HR Policy Agent",
            "response": (
                "⏱️ **Company People & Operations Notice**\n\n"
                "• **Core Working Hours**: 10:00 AM – 4:00 PM local time.\n"
                "• **Weekly Timesheet**: Due every Friday by 5:00 PM to ensure automated payroll processing.\n"
                "• **3-Tier Escalations**: In case of blockers, our automated routing directs you to the Primary Lead, Backup Lead (if on vacation), or Escalation Channel.\n"
                "• **IT Support**: Use the 'Report IT Ticket' quick action in the dashboard to submit high-priority hardware, network, or access requests directly."
            ),
            "suggested_actions": ["Check Timesheet Status", "Report IT Ticket", "Search Runbooks"],
        }


class PointToPersonAgent:
    @staticmethod
    def handle(employee: EmployeeRecord, query: str) -> Dict[str, Any]:
        contacts = OperationsService.get_points_of_contact(employee)
        buddy = contacts.get("buddy", {})
        manager = contacts.get("manager", {})
        it_supp = contacts.get("it_support", {})
        hr_supp = contacts.get("people_ops", {})
        escalations = contacts.get("domain_escalations", [])

        lines = [
            f"🤝 **Point to Person Connection: Direct Human Support for {employee.name}**\n",
            "When the AI Assistant cannot provide the exact answer you need, connect directly with these team leaders:\n",
            f"1. **Assigned Onboarding Buddy**: **{buddy.get('name')}** ({buddy.get('email')})",
            f"   • *Role*: {buddy.get('role')} | *Slack*: `{buddy.get('channel')}`",
            f"   • *Scope*: {buddy.get('scope')}\n",
            f"2. **Direct Reporting Manager**: **{manager.get('name')}** ({manager.get('email')})",
            f"   • *Role*: {manager.get('role')} | *Slack*: `{manager.get('channel')}`",
            f"   • *Scope*: {manager.get('scope')}\n",
            f"3. **IT Systems & IAM Admin**: **{it_supp.get('name')}** ({it_supp.get('email')}, `{it_supp.get('channel')}`)",
            f"   • *Scope*: {it_supp.get('scope')}\n",
            f"4. **People Operations (HR)**: **{hr_supp.get('name')}** ({hr_supp.get('email')}, `{hr_supp.get('channel')}`)",
            f"   • *Scope*: {hr_supp.get('scope')}\n",
            "🚨 **Technical Escalation Leads (with Automated Out-of-Office Routing)**:"
        ]

        for esc in escalations:
            status_tag = "🟢 Active" if esc["status"] == "PRIMARY_ASSIGNED" else "🟡 Backup Routed (Primary OOO)"
            lines.append(
                f"• **{esc['domain']}**: {esc['active_contact']} ({status_tag}) | Channel: `{esc['channel']}`"
            )

        return {
            "agent": "Point to Person Agent",
            "response": "\n".join(lines),
            "suggested_actions": ["Point of Contact", "Connect with Buddy", "Report IT Ticket", "View Pending Tasks"],
        }


class SupervisorAgent:
    @staticmethod
    def route(employee: EmployeeRecord, message: str) -> Dict[str, Any]:
        lower = message.lower()
        if any(w in lower for w in [
            "human", "person", "connect me", "point to person", "who can help",
            "contact person", "speak to someone", "representative", "agent can't help",
            "talk to human", "talk to someone", "real person", "escalate to human", "contact lead",
            "who do i talk to", "who do i ask", "point of contact"
        ]):
            return PointToPersonAgent.handle(employee, message)
        elif any(w in lower for w in ["onboard", "task", "checklist", "buddy", "status", "progress", "overdue", "video", "team progress", "rollup"]):
            return OnboardingAgent.handle(employee, message)
        elif any(w in lower for w in ["log", "code", "python", "typescript", "standards", "sql proxy", "idempotent", "git"]):
            return CodeMentorAgent.handle(employee, message)
        elif any(w in lower for w in ["timesheet", "hour", "vacation", "policy", "it ticket", "payroll", "escalat", "incident", "who to contact"]):
            return OpsAgent.handle(employee, message)
        else:
            # Default to Knowledge Mesh ACL pre-retrieval search
            return KnowledgeMeshAgent.search(employee, message)

