"""
Synthetic Operational Datasets: Timesheets, Incidents, and Team Directory Mesh.
"""

from typing import Dict, List
from app.models import TimesheetRecord, TimesheetStatus, IncidentRecord, IncidentSeverity, TeamEscalationContact


SYNTHETIC_TIMESHEETS: Dict[str, List[TimesheetRecord]] = {
    # Rahul Sharma (Payments) - Pending timesheet for current week
    "EMP-2026-001": [
        TimesheetRecord(
            timesheet_id="TS-2026-W36-001",
            employee_id="EMP-2026-001",
            period_start="2026-08-31",
            period_end="2026-09-04",
            hours_logged=32.0,
            status=TimesheetStatus.PENDING,
            due_date="2026-09-04",
        )
    ],

    # Maya Lin (Platform) - Submitted
    "EMP-2026-002": [
        TimesheetRecord(
            timesheet_id="TS-2026-W36-002",
            employee_id="EMP-2026-002",
            period_start="2026-08-31",
            period_end="2026-09-04",
            hours_logged=40.0,
            status=TimesheetStatus.SUBMITTED,
            due_date="2026-09-04",
        )
    ],

    # Liam Vance (Payments) - Overdue
    "EMP-2026-003": [
        TimesheetRecord(
            timesheet_id="TS-2026-W35-003",
            employee_id="EMP-2026-003",
            period_start="2026-08-24",
            period_end="2026-08-28",
            hours_logged=0.0,
            status=TimesheetStatus.OVERDUE,
            due_date="2026-08-28",
        )
    ],

    # Carlos Santana (DataOps) - Approved
    "EMP-2026-004": [
        TimesheetRecord(
            timesheet_id="TS-2026-W36-004",
            employee_id="EMP-2026-004",
            period_start="2026-08-31",
            period_end="2026-09-04",
            hours_logged=40.0,
            status=TimesheetStatus.APPROVED,
            due_date="2026-09-04",
        )
    ],
}


SYNTHETIC_INCIDENTS: List[IncidentRecord] = [
    IncidentRecord(
        incident_id="INC-2026-8801",
        created_by="EMP-2026-003",
        category="Database / Staging",
        summary="Staging PostgreSQL connection reset under load",
        severity=IncidentSeverity.MEDIUM,
        status="INVESTIGATING",
        assigned_team="Platform",
        created_at="2026-09-02T14:15:00Z",
    )
]


SYNTHETIC_TEAM_DIRECTORY: Dict[str, TeamEscalationContact] = {
    "kubernetes": TeamEscalationContact(
        domain="Kubernetes",
        primary_lead_name="Alex Chen",
        primary_email="alex.chen@company.com",
        primary_on_vacation=False,
        backup_lead_name="Sarah Connor",
        backup_email="sarah.c@company.com",
        backup_on_vacation=False,
        general_channel="#k8s-platform-support",
    ),
    "cloud sql": TeamEscalationContact(
        domain="Cloud SQL",
        primary_lead_name="David Miller",
        primary_email="david.miller@company.com",
        primary_on_vacation=True,
        backup_lead_name="Priya Nair",
        backup_email="priya.nair@company.com",
        backup_on_vacation=False,
        general_channel="#database-support-general",
    ),
    "iam & security": TeamEscalationContact(
        domain="IAM & Security",
        primary_lead_name="Elena Rostova",
        primary_email="elena.r@company.com",
        primary_on_vacation=True,
        backup_lead_name="Marcus Vance",
        backup_email="marcus.v@company.com",
        backup_on_vacation=True,
        general_channel="#secops-emergency-triage",
    ),
    "data pipelines": TeamEscalationContact(
        domain="Data Pipelines",
        primary_lead_name="Sofia Patel",
        primary_email="sofia.patel@company.com",
        primary_on_vacation=False,
        backup_lead_name="Jordan Lee",
        backup_email="jordan.lee@company.com",
        backup_on_vacation=True,
        general_channel="#data-engineering-help",
    ),
}
