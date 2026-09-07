"""
Synthetic Onboarding Tasks and Checklists Dataset.
Organized by employee ID and onboarding track.
"""

from typing import Dict, List
from app.models import OnboardingTask, OnboardingChecklist, TaskStatus


SYNTHETIC_ONBOARDING_CHECKLISTS: Dict[str, OnboardingChecklist] = {
    # Rahul Sharma (Payments - Backend Track) - 1 of 4 completed
    "EMP-2026-001": OnboardingChecklist(
        employee_id="EMP-2026-001",
        track="Backend",
        tasks=[
            OnboardingTask(
                task_id="TASK-001-SEC",
                title="Complete Corporate Security & Data Privacy Training",
                description="Review security policies, 2FA setup, and complete the compliance module.",
                status=TaskStatus.COMPLETED,
                due_days_after_start=1,
                completed_at="2026-09-01T10:30:00Z",
                category="Security & Compliance",
                action_link="https://learning.internal.company.com/courses/sec-2026",
            ),
            OnboardingTask(
                task_id="TASK-001-ENV",
                title="Set up Local Dev Environment & Cloud SQL Proxy",
                description="Install gcloud CLI, Docker, and configure Cloud SQL Auth Proxy for PostgreSQL staging.",
                status=TaskStatus.PENDING,
                due_days_after_start=2,
                category="Development Setup",
                action_link="gs://patchamomma-knowledge-mesh/runbooks/dev_environment_setup.md",
            ),
            OnboardingTask(
                task_id="TASK-001-BUDDY",
                title="Schedule 1:1 Intro with Onboarding Buddy (Priya Nair)",
                description="Connect with Priya for payments architecture overview and team introduction.",
                status=TaskStatus.PENDING,
                due_days_after_start=3,
                category="Team Integration",
                action_link="mailto:priya.nair@company.com",
            ),
            OnboardingTask(
                task_id="TASK-001-GIT",
                title="Submit first sandbox PR to payments-core repo",
                description="Clone repository, make standard JSON logger improvement, and open test PR.",
                status=TaskStatus.PENDING,
                due_days_after_start=5,
                category="First Milestone",
                action_link="https://github.com/company/payments-core",
            ),
        ],
        completed_count=1,
        total_count=4,
        next_pending_task=OnboardingTask(
            task_id="TASK-001-ENV",
            title="Set up Local Dev Environment & Cloud SQL Proxy",
            description="Install gcloud CLI, Docker, and configure Cloud SQL Auth Proxy for PostgreSQL staging.",
            status=TaskStatus.PENDING,
            due_days_after_start=2,
            category="Development Setup",
            action_link="gs://patchamomma-knowledge-mesh/runbooks/dev_environment_setup.md",
        ),
    ),

    # Maya Lin (Platform Intern) - 0 of 3 completed
    "EMP-2026-002": OnboardingChecklist(
        employee_id="EMP-2026-002",
        track="Platform",
        tasks=[
            OnboardingTask(
                task_id="TASK-002-SEC",
                title="Complete Corporate Security & Data Privacy Training",
                description="Complete mandatory security basics and IAM access policies.",
                status=TaskStatus.PENDING,
                due_days_after_start=1,
                category="Security & Compliance",
                action_link="https://learning.internal.company.com/courses/sec-2026",
            ),
            OnboardingTask(
                task_id="TASK-002-GCP",
                title="Configure Google Cloud SDK & GKE Cluster Access",
                description="Set up gcloud auth and kubectl credentials for staging Kubernetes clusters.",
                status=TaskStatus.PENDING,
                due_days_after_start=2,
                category="Infrastructure Setup",
                action_link="gs://patchamomma-knowledge-mesh/runbooks/kubernetes_cluster_triage.md",
            ),
            OnboardingTask(
                task_id="TASK-002-BUDDY",
                title="Schedule 1:1 Intro with Onboarding Buddy (David Miller)",
                description="Introductory pairing session on infrastructure pipelines.",
                status=TaskStatus.PENDING,
                due_days_after_start=3,
                category="Team Integration",
                action_link="mailto:david.miller@company.com",
            ),
        ],
        completed_count=0,
        total_count=3,
        next_pending_task=OnboardingTask(
            task_id="TASK-002-SEC",
            title="Complete Corporate Security & Data Privacy Training",
            description="Complete mandatory security basics and IAM access policies.",
            status=TaskStatus.PENDING,
            due_days_after_start=1,
            category="Security & Compliance",
            action_link="https://learning.internal.company.com/courses/sec-2026",
        ),
    ),

    # Liam Vance (Payments Engineer) - 3 of 4 completed
    "EMP-2026-003": OnboardingChecklist(
        employee_id="EMP-2026-003",
        track="Backend",
        tasks=[
            OnboardingTask(
                task_id="TASK-003-SEC",
                title="Complete Corporate Security & Data Privacy Training",
                description="Review security policies and 2FA.",
                status=TaskStatus.COMPLETED,
                due_days_after_start=1,
                completed_at="2026-08-16T14:00:00Z",
                category="Security & Compliance",
            ),
            OnboardingTask(
                task_id="TASK-003-ENV",
                title="Set up Local Dev Environment & Cloud SQL Proxy",
                description="Local setup and database connectivity.",
                status=TaskStatus.COMPLETED,
                due_days_after_start=2,
                completed_at="2026-08-17T11:00:00Z",
                category="Development Setup",
            ),
            OnboardingTask(
                task_id="TASK-003-BUDDY",
                title="Schedule 1:1 Intro with Onboarding Buddy (Priya Nair)",
                description="Initial sync with Priya.",
                status=TaskStatus.COMPLETED,
                due_days_after_start=3,
                completed_at="2026-08-18T16:00:00Z",
                category="Team Integration",
            ),
            OnboardingTask(
                task_id="TASK-003-PR",
                title="Complete first production Payments PR review",
                description="Peer review of payment tokenization routine.",
                status=TaskStatus.PENDING,
                due_days_after_start=10,
                category="First Milestone",
            ),
        ],
        completed_count=3,
        total_count=4,
        next_pending_task=OnboardingTask(
            task_id="TASK-003-PR",
            title="Complete first production Payments PR review",
            description="Peer review of payment tokenization routine.",
            status=TaskStatus.PENDING,
            due_days_after_start=10,
            category="First Milestone",
        ),
    ),

    # Carlos Santana (DataOps) - Fully completed
    "EMP-2026-004": OnboardingChecklist(
        employee_id="EMP-2026-004",
        track="DataOps",
        tasks=[
            OnboardingTask(
                task_id="TASK-004-ALL",
                title="All DataOps Onboarding Modules",
                description="Historical completion of all onboarding requirements.",
                status=TaskStatus.COMPLETED,
                due_days_after_start=1,
                completed_at="2024-05-15T09:00:00Z",
                category="General",
            )
        ],
        completed_count=1,
        total_count=1,
        next_pending_task=None,
    ),
}
