"""
Onboarding Agent Tools.
Enforces zero-trust context binding: caller identity is retrieved from contextvars, never from LLM arguments.
"""

import logging
from typing import Dict, Any, Optional

from app.core import context
from app.dependencies import onboarding_service, employee_service

logger = logging.getLogger("patchamomma.agents.tools.onboarding")


def get_my_onboarding_status() -> str:
    """
    Retrieves the active employee's personal onboarding checklist, progress count, and next pending task.
    ZERO-TRUST: Uses authenticated context employee. No employee_id parameter accepted from model.
    """
    actor = context.get_current_employee()
    try:
        checklist = onboarding_service.get_employee_checklist(actor, actor.employee_id)
        next_task_info = (
            f"Next Pending Task: [{checklist.next_pending_task.task_id}] {checklist.next_pending_task.title}\n"
            f"Description: {checklist.next_pending_task.description}\n"
            f"Action Link: {checklist.next_pending_task.action_link or 'N/A'}"
            if checklist.next_pending_task
            else "All onboarding tasks are COMPLETED!"
        )

        tasks_summary = "\n".join(
            f"- [{t.status.value}] {t.title} (ID: {t.task_id})" for t in checklist.tasks
        )

        return (
            f"📋 **Onboarding Progress for {actor.name} ({actor.team} Team)**\n"
            f"Completed: {checklist.completed_count} of {checklist.total_count} tasks ({int((checklist.completed_count / checklist.total_count) * 100)}%)\n\n"
            f"**Task Breakdown**:\n{tasks_summary}\n\n"
            f"**Immediate Action**:\n{next_task_info}"
        )
    except Exception as e:
        logger.error(f"get_my_onboarding_status failed: {e}")
        return f"Error retrieving onboarding checklist: {str(e)}"


def complete_my_onboarding_task(task_id: str) -> str:
    """
    Marks a specific onboarding task as completed for the authenticated employee.
    Args:
        task_id: The unique task identifier (e.g. 'TASK-001-SEC')
    """
    actor = context.get_current_employee()
    try:
        updated = onboarding_service.complete_onboarding_task(actor, task_id.strip())
        next_step = f"Next task: {updated.next_pending_task.title}" if updated.next_pending_task else "You have finished all checklist items!"
        return (
            f"✅ **Task '{task_id}' Marked Completed!**\n"
            f"Current progress: {updated.completed_count} of {updated.total_count} tasks.\n"
            f"{next_step}"
        )
    except Exception as e:
        logger.warning(f"complete_my_onboarding_task failed: {e}")
        return f"Could not complete task '{task_id}': {str(e)}"


def get_team_onboarding_progress() -> str:
    """
    Retrieves the onboarding progress rollup for all members of the caller's team.
    Restricted to Managers and HR. Server-side authorization is strictly enforced.
    """
    actor = context.get_current_employee()
    try:
        summary = onboarding_service.get_team_onboarding_progress(actor)
        member_lines = []
        for m in summary.members:
            status_symbol = "✅" if m.completed_count == m.total_count else ("🚨 BLOCKED" if m.is_blocked else "⏳ IN PROGRESS")
            pending_str = f"Pending: {', '.join(m.pending_tasks)}" if m.pending_tasks else "All tasks done"
            member_lines.append(f"- **{m.name}** ({m.job_role}): {status_symbol} [{m.completed_count}/{m.total_count}] - {pending_str}")

        return (
            f"👥 **Team Onboarding Rollup: {summary.team_name} (Manager: {summary.manager_name})**\n"
            f"Total Members: {summary.total_team_members} | Fully Onboarded: {summary.fully_onboarded_count}\n\n"
            + "\n".join(member_lines)
        )
    except Exception as e:
        logger.warning(f"get_team_onboarding_progress denied or failed: {e}")
        return f"Authorization / Lookup Error: {str(e)}"
