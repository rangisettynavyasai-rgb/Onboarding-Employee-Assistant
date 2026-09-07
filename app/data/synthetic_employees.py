"""
Synthetic Employee Directory for Patchamomma 2026.
Contains representative personas covering all roles (Employee, Manager, HR, IT) and teams.
"""

from typing import Dict, List
from app.models import EmployeeRecord, AuthorizationRole, OnboardingStatus


SYNTHETIC_EMPLOYEES: Dict[str, EmployeeRecord] = {
    # 1. Day-1 New Joiner (Payments Engineer)
    "EMP-2026-001": EmployeeRecord(
        employee_id="EMP-2026-001",
        google_subject="google-sub-rahul-001",
        email="rahul.sharma@company.com",
        name="Rahul Sharma",
        department="Engineering",
        team="Payments",
        job_role="Software Engineer I",
        authorization_role=AuthorizationRole.EMPLOYEE,
        manager_id="EMP-2026-010",
        location="Seattle, WA",
        joining_date="2026-09-01",
        onboarding_status=OnboardingStatus.IN_PROGRESS,
        is_day_one=True,
        assigned_buddy_name="Priya Nair",
        assigned_buddy_email="priya.nair@company.com",
        onboarding_track="Backend",
    ),

    # 2. Day-1 Intern (Platform Infrastructure)
    "EMP-2026-002": EmployeeRecord(
        employee_id="EMP-2026-002",
        google_subject="google-sub-maya-002",
        email="maya.lin@company.com",
        name="Maya Lin",
        department="Infrastructure",
        team="Platform",
        job_role="Cloud Infrastructure Intern",
        authorization_role=AuthorizationRole.EMPLOYEE,
        manager_id="EMP-2026-005",
        location="San Francisco, CA",
        joining_date="2026-09-01",
        onboarding_status=OnboardingStatus.IN_PROGRESS,
        is_day_one=True,
        assigned_buddy_name="David Miller",
        assigned_buddy_email="david.miller@company.com",
        onboarding_track="Platform",
    ),

    # 3. New Hire with partial onboarding completed (Payments Engineer)
    "EMP-2026-003": EmployeeRecord(
        employee_id="EMP-2026-003",
        google_subject="google-sub-liam-003",
        email="liam.vance@company.com",
        name="Liam Vance",
        department="Engineering",
        team="Payments",
        job_role="Software Engineer II",
        authorization_role=AuthorizationRole.EMPLOYEE,
        manager_id="EMP-2026-010",
        location="Austin, TX",
        joining_date="2026-08-15",
        onboarding_status=OnboardingStatus.IN_PROGRESS,
        is_day_one=False,
        assigned_buddy_name="Priya Nair",
        assigned_buddy_email="priya.nair@company.com",
        onboarding_track="Backend",
    ),

    # 4. Senior Operational Staff Engineer (DataOps)
    "EMP-2026-004": EmployeeRecord(
        employee_id="EMP-2026-004",
        google_subject="google-sub-carlos-004",
        email="carlos.s@company.com",
        name="Carlos Santana",
        department="Data Platforms",
        team="DataOps",
        job_role="Senior Staff Data Engineer",
        authorization_role=AuthorizationRole.EMPLOYEE,
        manager_id="EMP-2026-005",
        location="New York, NY",
        joining_date="2024-05-10",
        onboarding_status=OnboardingStatus.COMPLETED,
        is_day_one=False,
        assigned_buddy_name=None,
        assigned_buddy_email=None,
        onboarding_track="DataOps",
    ),

    # 5. Engineering Director / Manager (Platform Team Manager)
    "EMP-2026-005": EmployeeRecord(
        employee_id="EMP-2026-005",
        google_subject="google-sub-alex-005",
        email="alex.chen@company.com",
        name="Alex Chen",
        department="Infrastructure",
        team="Platform",
        job_role="Director of Platform Engineering",
        authorization_role=AuthorizationRole.MANAGER,
        manager_id=None,
        location="San Francisco, CA",
        joining_date="2023-01-15",
        onboarding_status=OnboardingStatus.COMPLETED,
        is_day_one=False,
        assigned_buddy_name=None,
        assigned_buddy_email=None,
        onboarding_track="Platform",
    ),

    # 6. Tech Lead & Onboarding Buddy (Payments)
    "EMP-2026-006": EmployeeRecord(
        employee_id="EMP-2026-006",
        google_subject="google-sub-priya-006",
        email="priya.nair@company.com",
        name="Priya Nair",
        department="Engineering",
        team="Payments",
        job_role="Staff Software Engineer & Tech Lead",
        authorization_role=AuthorizationRole.EMPLOYEE,
        manager_id="EMP-2026-010",
        location="Seattle, WA",
        joining_date="2023-08-01",
        onboarding_status=OnboardingStatus.COMPLETED,
        is_day_one=False,
        assigned_buddy_name=None,
        assigned_buddy_email=None,
        onboarding_track="Backend",
    ),

    # 7. Security Engineer (Platform / SecOps)
    "EMP-2026-007": EmployeeRecord(
        employee_id="EMP-2026-007",
        google_subject="google-sub-elena-007",
        email="elena.r@company.com",
        name="Elena Rostova",
        department="Security",
        team="Platform",
        job_role="Senior SecOps & Cloud IAM Engineer",
        authorization_role=AuthorizationRole.EMPLOYEE,
        manager_id="EMP-2026-005",
        location="Boston, MA",
        joining_date="2024-01-10",
        onboarding_status=OnboardingStatus.COMPLETED,
        is_day_one=False,
        assigned_buddy_name=None,
        assigned_buddy_email=None,
        onboarding_track="Platform",
    ),

    # 8. IT Administrator (IT Role)
    "EMP-2026-008": EmployeeRecord(
        employee_id="EMP-2026-008",
        google_subject="google-sub-marcus-008",
        email="marcus.v@company.com",
        name="Marcus Vance",
        department="IT Services",
        team="IT",
        job_role="Lead IT Systems Administrator",
        authorization_role=AuthorizationRole.IT,
        manager_id=None,
        location="Chicago, IL",
        joining_date="2023-11-01",
        onboarding_status=OnboardingStatus.COMPLETED,
        is_day_one=False,
        assigned_buddy_name=None,
        assigned_buddy_email=None,
        onboarding_track="General",
    ),

    # 9. HR Specialist (HR Role)
    "EMP-2026-009": EmployeeRecord(
        employee_id="EMP-2026-009",
        google_subject="google-sub-amanda-009",
        email="amanda.w@company.com",
        name="Amanda Walker",
        department="People Operations",
        team="HR",
        job_role="Senior People Ops Specialist",
        authorization_role=AuthorizationRole.HR,
        manager_id=None,
        location="New York, NY",
        joining_date="2023-04-15",
        onboarding_status=OnboardingStatus.COMPLETED,
        is_day_one=False,
        assigned_buddy_name=None,
        assigned_buddy_email=None,
        onboarding_track="General",
    ),

    # 10. Engineering Manager (Payments Team Manager)
    "EMP-2026-010": EmployeeRecord(
        employee_id="EMP-2026-010",
        google_subject="google-sub-sarah-010",
        email="sarah.j@company.com",
        name="Sarah Jenkins",
        department="Engineering",
        team="Payments",
        job_role="Engineering Manager - Payments",
        authorization_role=AuthorizationRole.MANAGER,
        manager_id=None,
        location="Seattle, WA",
        joining_date="2022-09-01",
        onboarding_status=OnboardingStatus.COMPLETED,
        is_day_one=False,
        assigned_buddy_name=None,
        assigned_buddy_email=None,
        onboarding_track="Backend",
    ),
}


def get_all_employees() -> List[EmployeeRecord]:
    """Returns a list of all synthetic employee records."""
    return list(SYNTHETIC_EMPLOYEES.values())
