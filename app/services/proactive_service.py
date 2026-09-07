"""
Proactive Assistant & Notification Service.
Generates personalized Day-1 orientation packages, pending task reminders, and timesheet notifications.
"""

import logging
from typing import Dict, Any, Optional

from app.config import settings
from app.core.logging import log_audit_event
from app.models import EmployeeRecord, OnboardingChecklist, OnboardingStatus
from app.services.onboarding_service import OnboardingService
from app.services.timesheet_service import TimesheetService

logger = logging.getLogger("patchamomma.services.proactive")


class ProactiveService:
    """Generates proactive landing messages and actionable notifications."""

    def __init__(self, onboarding_service: OnboardingService, timesheet_service: TimesheetService):
        self.onboarding_service = onboarding_service
        self.timesheet_service = timesheet_service

    def generate_proactive_landing(self, employee: EmployeeRecord) -> Dict[str, Any]:
        """
        Builds a proactive Day-1 landing kit or welcome-back greeting.
        """
        checklist: Optional[OnboardingChecklist] = None
        try:
            checklist = self.onboarding_service.get_employee_checklist(employee, employee.employee_id)
        except Exception:
            pass

        timesheet_info = self.timesheet_service.get_timesheet_status(employee, employee.employee_id)

        if employee.is_day_one:
            gcs_folder = f"gs://{settings.GCS_KNOWLEDGE_BUCKET}/onboarding/{employee.team.lower()}"
            next_task_text = f"Your next task is: **{checklist.next_pending_task.title}**" if checklist and checklist.next_pending_task else "All Day 1 tasks are initialized."

            greeting = (
                f"🎉 **Welcome to Patchamomma 2026, {employee.name}! (Day 1 Onboarding Kickoff)**\n\n"
                f"We are thrilled to welcome you to the **{employee.team}** team as a **{employee.job_role}**.\n\n"
                f"### 🚀 Your Day 1 Orientation Kit:\n"
                f"1. **Onboarding Status**: Completed {checklist.completed_count if checklist else 0} of {checklist.total_count if checklist else 4} tasks.\n"
                f"   - {next_task_text}\n"
                f"2. **Team Knowledge Mesh Docs**:\n"
                f"   - [`{gcs_folder}/day1_getting_started.pdf`]({gcs_folder}/day1_getting_started.pdf)\n"
                f"   - [`{gcs_folder}/architecture_overview_2026.md`]({gcs_folder}/architecture_overview_2026.md)\n"
                f"3. **Walkthrough Video Asset**:\n"
                f"   - Link: `gs://{settings.GCS_KNOWLEDGE_BUCKET}/videos/onboarding/{employee.onboarding_track.lower()}_deepdive.mp4`\n"
                f"   - ⏱️ **Key Timestamp**: Skip to **Minute 04:15** for environment setup and **Minute 18:45** for Cloud SQL Proxy setup.\n"
                f"4. **Your Onboarding Buddy**:\n"
                f"   - **{employee.assigned_buddy_name or 'Priya Nair'}** ({employee.assigned_buddy_email or 'priya.nair@company.com'}) - Reach out anytime!\n\n"
                f"Ask me anything about setup, code standards, or company documentation!"
            )
        else:
            completed_str = f"You have completed {checklist.completed_count} of {checklist.total_count} onboarding tasks." if checklist and checklist.completed_count < checklist.total_count else "All onboarding tasks completed."
            ts_reminder = f"\n⚠️ *Reminder*: {timesheet_info['message']}" if timesheet_info.get("action_required") else ""

            greeting = (
                f"👋 Welcome back, **{employee.name}** ({employee.job_role}, {employee.team}).\n"
                f"{completed_str}{ts_reminder}\n"
                f"How can I assist your workflow or codebase questions today?"
            )

        log_audit_event("PROACTIVE_LANDING", employee.employee_id, "GENERATE_GREETING", "ALLOWED", "LANDING_PAGE")

        return {
            "employee_id": employee.employee_id,
            "name": employee.name,
            "is_day_one": employee.is_day_one,
            "proactive_greeting": greeting,
            "onboarding_summary": checklist.model_dump() if checklist else None,
            "timesheet_status": timesheet_info,
        }
