#!/usr/bin/env python3
"""
Company AI Assistant: Comprehensive In-Memory Datasets & BigQuery Seed Catalog
Synchronized with tables in company-internal.employee_ai
"""
from typing import Dict, List, Any, Optional
from backend.models import (
    EmployeeRecord, AuthorizationRole, OnboardingTask, TaskStatus,
    KnowledgeAsset, KnowledgeChunk, TimesheetRecord, TimesheetStatus,
    IncidentRecord, IncidentSeverity
)

# 1. Employee Directory
EMPLOYEES: Dict[str, EmployeeRecord] = {
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
        onboarding_status="IN_PROGRESS",
        is_day_one=True,
        assigned_buddy_name="Priya Nair",
        assigned_buddy_email="priya.nair@company.com",
        onboarding_track="Backend",
    ),
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
        onboarding_status="IN_PROGRESS",
        is_day_one=True,
        assigned_buddy_name="David Miller",
        assigned_buddy_email="david.miller@company.com",
        onboarding_track="Platform",
    ),
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
        onboarding_status="IN_PROGRESS",
        is_day_one=False,
        assigned_buddy_name="Priya Nair",
        assigned_buddy_email="priya.nair@company.com",
        onboarding_track="Backend",
    ),
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
        onboarding_status="COMPLETED",
        is_day_one=False,
        assigned_buddy_name=None,
        assigned_buddy_email=None,
        onboarding_track="DataOps",
    ),
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
        onboarding_status="COMPLETED",
        is_day_one=False,
        assigned_buddy_name=None,
        assigned_buddy_email=None,
        onboarding_track="Platform",
    ),
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
        onboarding_status="COMPLETED",
        is_day_one=False,
        assigned_buddy_name=None,
        assigned_buddy_email=None,
        onboarding_track="Backend",
    ),
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
        onboarding_status="COMPLETED",
        is_day_one=False,
        assigned_buddy_name=None,
        assigned_buddy_email=None,
        onboarding_track="Platform",
    ),
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
        onboarding_status="COMPLETED",
        is_day_one=False,
        assigned_buddy_name=None,
        assigned_buddy_email=None,
        onboarding_track="General",
    ),
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
        onboarding_status="COMPLETED",
        is_day_one=False,
        assigned_buddy_name=None,
        assigned_buddy_email=None,
        onboarding_track="General",
    ),
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
        onboarding_status="COMPLETED",
        is_day_one=False,
        assigned_buddy_name=None,
        assigned_buddy_email=None,
        onboarding_track="Backend",
    ),
}

# 2. Onboarding Tasks with Due Dates
ONBOARDING_TASKS: Dict[str, List[OnboardingTask]] = {
    "EMP-2026-001": [
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
            action_link="gs://company-knowledge-mesh/runbooks/dev_environment_setup.md",
        ),
        OnboardingTask(
            task_id="TASK-001-BUDDY",
            title="Schedule 1:1 Intro with Onboarding Buddy (Priya Nair)",
            description="Connect with Priya for payments architecture overview and team introduction.",
            status=TaskStatus.PENDING,
            due_days_after_start=4,
            category="Team Integration",
            action_link="mailto:priya.nair@company.com",
        ),
        OnboardingTask(
            task_id="TASK-001-GIT",
            title="Submit first sandbox PR to payments-core repo",
            description="Clone repository, make standard JSON logger improvement, and open test PR.",
            status=TaskStatus.PENDING,
            due_days_after_start=10,
            category="First Milestone",
            action_link="https://github.com/company/payments-core",
        ),
    ],
    "EMP-2026-002": [
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
            action_link="gs://company-knowledge-mesh/runbooks/kubernetes_cluster_triage.md",
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
    "EMP-2026-003": [
        OnboardingTask(
            task_id="TASK-003-SEC",
            title="Complete Corporate Security & Data Privacy Training",
            description="Compliance certification.",
            status=TaskStatus.COMPLETED,
            due_days_after_start=1,
            completed_at="2026-08-16T09:00:00Z",
            category="Security",
        ),
        OnboardingTask(
            task_id="TASK-003-ENV",
            title="Set up Local Dev Environment & Cloud SQL Proxy",
            description="Setup postgres proxy and secrets.",
            status=TaskStatus.COMPLETED,
            due_days_after_start=2,
            completed_at="2026-08-17T11:00:00Z",
            category="Setup",
        ),
        OnboardingTask(
            task_id="TASK-003-BUDDY",
            title="Schedule 1:1 Intro with Onboarding Buddy",
            description="1:1 with buddy.",
            status=TaskStatus.COMPLETED,
            due_days_after_start=3,
            completed_at="2026-08-18T14:00:00Z",
            category="Integration",
        ),
        OnboardingTask(
            task_id="TASK-003-GIT",
            title="Submit first sandbox PR to payments-core repo",
            description="Open PR.",
            status=TaskStatus.PENDING,
            due_days_after_start=5,
            category="Milestone",
        ),
    ],
}

# 3. Knowledge Catalog & ACL Mesh
KNOWLEDGE_CATALOG: List[KnowledgeAsset] = [
    KnowledgeAsset(
        document_id="DOC-ALL-001",
        title="Company Code of Conduct, Workplace Guidelines & Hours",
        source="Corporate People Operations Policies",
        gcs_uri="gs://company-knowledge-mesh/company/code_of_conduct_2026.md",
        team="ALL",
        access_level="employee",
        document_type="Policy",
        owner="People Operations Team",
        description="Comprehensive workplace guidelines, core hours, timesheet submission policies, and cultural values.",
        chunks=[
            KnowledgeChunk(
                chunk_id="CHK-ALL-001-1",
                document_id="DOC-ALL-001",
                chunk_index=0,
                content=(
                    "# Company Code of Conduct & Workplace Standards\n\n"
                    "## Core Values\n"
                    "1. **Psychological Safety & Respect**: We foster an inclusive environment where questions are celebrated and failure is treated as a learning opportunity.\n"
                    "2. **Customer & Team Obsession**: Deliver high-reliability services that simplify work for teammates and external customers.\n"
                    "3. **Radical Candor with Empathy**: Direct, constructive feedback delivered with genuine care.\n\n"
                    "## Working Hours & Flexibility\n"
                    "- **Core Hours**: 10:00 AM – 4:00 PM in your local time zone for synchronous meetings and team alignment.\n"
                    "- **Flexible Bands**: Remaining hours can be structured flexibly around personal productivity and time zone needs.\n\n"
                    "## Weekly Timesheet Policy\n"
                    "- All hourly and salaried employees must review and finalize their weekly timesheet by **Friday at 5:00 PM local time**.\n"
                    "- Timesheets ensure timely payroll processing, project cost tracking, and compliance.\n"
                    "- Direct questions to People Operations at `people-ops@company.com`."
                ),
                team="ALL",
                access_level="employee",
            )
        ],
    ),
    KnowledgeAsset(
        document_id="DOC-ALL-002",
        title="Engineering Coding & Structured Logging Standards",
        source="Engineering Guild Architecture Wiki",
        gcs_uri="gs://company-knowledge-mesh/engineering/logging_standards_2026.md",
        team="ALL",
        access_level="employee",
        document_type="Technical Standard",
        owner="Engineering Architecture Guild",
        description="Mandatory structured JSON logging (RFC-5424), Conventional Commits, and CI pipeline quality gates.",
        chunks=[
            KnowledgeChunk(
                chunk_id="CHK-ALL-002-1",
                document_id="DOC-ALL-002",
                chunk_index=0,
                content=(
                    "# Engineering Coding & Structured Logging Standards\n\n"
                    "## 1. Zero Raw Print Policy\n"
                    "Never commit raw `print(...)` in Python or `console.log(...)` in TypeScript to production microservices. "
                    "Unstructured log lines break downstream ingestion into Google Cloud Logging and BigQuery telemetry pipelines.\n\n"
                    "## 2. Standard Structured JSON Logging Format (RFC-5424)\n"
                    "All application logs must be serialized as JSON objects with the following schema:\n"
                    "```python\n"
                    "import logging, json\n"
                    "logger = logging.getLogger('payments-service')\n"
                    "logger.info(json.dumps({\n"
                    "    'event': 'PAYMENT_TRANSACTION_INITIATED',\n"
                    "    'trace_id': trace_id,\n"
                    "    'user_id': user_id,\n"
                    "    'amount_cents': 2500,\n"
                    "    'status': 'SUCCESS'\n"
                    "}))\n"
                    "```\n\n"
                    "## 3. Database Security & Credentials\n"
                    "- **No hardcoded credentials**: Never store database passwords or service account keys in repositories.\n"
                    "- **Cloud SQL Auth Proxy**: Connect to Cloud SQL via `127.0.0.1:5432` using IAM database authentication and Google Cloud Secret Manager.\n\n"
                    "## 4. Git & Code Review Rules\n"
                    "- Conventional Commits required: `feat(scope): message`, `fix(scope): message`.\n"
                    "- Every PR requires at least 1 peer approval and passing automated CI checks."
                ),
                team="ALL",
                access_level="employee",
            )
        ],
    ),
    KnowledgeAsset(
        document_id="DOC-PAY-001",
        title="Payments Event Ledger & Idempotency Architecture",
        source="GitHub engineering/payments-core",
        gcs_uri="gs://company-knowledge-mesh/payments/architecture_overview_2026.md",
        team="Payments",
        access_level="employee",
        document_type="Technical Blueprint",
        owner="Payments Guild Lead",
        description="High-throughput double-entry bookkeeping engine, Idempotency-Key headers, and Cloud SQL PostgreSQL specifications.",
        chunks=[
            KnowledgeChunk(
                chunk_id="CHK-PAY-001-1",
                document_id="DOC-PAY-001",
                chunk_index=0,
                content=(
                    "# Payments Architecture Blueprint: Event Ledger & Idempotency\n\n"
                    "## Overview\n"
                    "The Payments Core service handles credit, debit, and settlement transactions across global payment gateways. "
                    "All accounting operations follow an immutable double-entry bookkeeping model.\n\n"
                    "## 1. Idempotency Key Specification\n"
                    "- Every mutative endpoint (`POST /v1/charges`, `POST /v1/transfers`) requires an `Idempotency-Key: <UUID-v4>` header.\n"
                    "- Redis KV cluster caches request payloads and status codes for a **24-hour TTL** window.\n"
                    "- In the event of network retries, duplicate requests return the cached response without re-executing funds movement.\n\n"
                    "## 2. Cloud SQL Persistence & BigQuery Streaming\n"
                    "- Primary datastore: Cloud SQL PostgreSQL instance running with automated failover.\n"
                    "- Change Data Capture (CDC): Events are streamed in real time to BigQuery `payments_events_ledger` table for audit reconciliation."
                ),
                team="Payments",
                access_level="employee",
            )
        ],
    ),
    KnowledgeAsset(
        document_id="DOC-PLT-001",
        title="Kubernetes Staging Cluster Triage & Service Mesh Runbook",
        source="Confluence Platform Runbooks",
        gcs_uri="gs://company-knowledge-mesh/platform/k8s_triage_guide.md",
        team="Platform",
        access_level="employee",
        document_type="Runbook",
        owner="Platform Reliability Team",
        description="GKE cluster incident response, Istio routing rules, and Cloud SQL Auth Proxy sidecar rotation procedures.",
        chunks=[
            KnowledgeChunk(
                chunk_id="CHK-PLT-001-1",
                document_id="DOC-PLT-001",
                chunk_index=0,
                content=(
                    "# Platform Runbook: Kubernetes Staging Cluster Triage\n\n"
                    "## Common Alert: 5xx Spike on Ingress\n"
                    "1. **Check Gateway Logs**:\n"
                    "   `kubectl logs -l app=payment-gateway -c istio-proxy -n staging --tail=100`\n"
                    "2. **Verify Cloud SQL Proxy Sidecar**:\n"
                    "   Check pod sidecar status: `kubectl get pods -n staging -o wide`\n"
                    "   Inspect proxy logs: `kubectl logs <pod-name> -c cloud-sql-proxy -n staging`\n"
                    "3. **Restarting Unhealthy Pods**:\n"
                    "   `kubectl rollout restart deployment/payment-gateway -n staging`\n"
                    "4. **Escalation**:\n"
                    "   If latency exceeds 500ms or error rate > 1%, page the on-call engineer via `#platform-incidents`."
                ),
                team="Platform",
                access_level="employee",
            )
        ],
    ),
    KnowledgeAsset(
        document_id="DOC-MGR-001",
        title="Performance Management & Compensation Review Guidelines",
        source="HR Internal Shared Drive",
        gcs_uri="gs://company-knowledge-mesh/hr/compensation_guidelines_2026.pdf",
        team="ALL",
        access_level="manager",
        document_type="Management Guideline",
        owner="VP People Operations",
        description="Confidential managerial document detailing compensation bands, calibration processes, and bonus criteria.",
        chunks=[
            KnowledgeChunk(
                chunk_id="CHK-MGR-001-1",
                document_id="DOC-MGR-001",
                chunk_index=0,
                content=(
                    "# Managerial Compensation & Performance Guidelines\n\n"
                    "*(Confidential - Restricted to Managers and HR)*\n\n"
                    "## 1. Annual Calibration Timeline\n"
                    "- Self & Peer Reviews: Open September 15 – October 5.\n"
                    "- Manager Assessment & Rating Submission: Due October 15.\n"
                    "- Department Calibration Sessions: October 20 – October 28.\n"
                    "- Merit & Equity Statements Issued: November 15.\n\n"
                    "## 2. Rating Rubric\n"
                    "- Level 1: Developing / Needs Coaching\n"
                    "- Level 2: Fully Meets Role Expectations\n"
                    "- Level 3: Frequently Exceeds Expectations / Force Multiplier\n"
                    "- Promotion packages require 2 peer endorsements, manager rationale, and director signoff."
                ),
                team="ALL",
                access_level="manager",
            )
        ],
    ),
]

# 4. Timesheet Records
TIMESHEETS: Dict[str, List[TimesheetRecord]] = {
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

# 5. Incidents
INCIDENTS: List[IncidentRecord] = [
    IncidentRecord(
        incident_id="INC-2026-8801",
        created_by="EMP-2026-003",
        category="Database / Staging",
        summary="Staging PostgreSQL connection reset under load",
        severity=IncidentSeverity.MEDIUM,
        status="OPEN",
        assigned_team="Platform",
        created_at="2026-09-02T14:22:00Z",
    )
]

# 6. Team Escalation Directory
TEAM_DIRECTORY: Dict[str, Dict[str, Any]] = {
    "Cloud SQL": {
        "domain": "Cloud SQL",
        "primary_lead_name": "Alex Chen",
        "primary_email": "alex.chen@company.com",
        "primary_on_vacation": False,
        "backup_lead_name": "David Miller",
        "backup_email": "david.miller@company.com",
        "backup_on_vacation": False,
        "general_channel": "#help-infrastructure",
    },
    "Kubernetes": {
        "domain": "Kubernetes",
        "primary_lead_name": "Elena Rostova",
        "primary_email": "elena.r@company.com",
        "primary_on_vacation": True,
        "backup_lead_name": "Carlos Santana",
        "backup_email": "carlos.s@company.com",
        "backup_on_vacation": False,
        "general_channel": "#help-kubernetes",
    },
    "IAM & Security": {
        "domain": "IAM & Security",
        "primary_lead_name": "Elena Rostova",
        "primary_email": "elena.r@company.com",
        "primary_on_vacation": True,
        "backup_lead_name": "Marcus Vance",
        "backup_email": "marcus.v@company.com",
        "backup_on_vacation": True,
        "general_channel": "#security-triage",
    },
    "Data Pipelines": {
        "domain": "Data Pipelines",
        "primary_lead_name": "Carlos Santana",
        "primary_email": "carlos.s@company.com",
        "primary_on_vacation": False,
        "backup_lead_name": "Alex Chen",
        "backup_email": "alex.chen@company.com",
        "backup_on_vacation": False,
        "general_channel": "#dataplat-support",
    },
}

# 7. Knowledge Insights
KNOWLEDGE_INSIGHTS: List[Dict[str, Any]] = [
    {
        "insight_id": "INSIGHT-2026-001",
        "doc_id": "DOC-ALL-002",
        "title": "Mandatory Structured JSON Logging v2.4 Enforced",
        "category": "STANDARDS",
        "summary": "All microservices must emit logs formatted in RFC-5424 JSON with trace context. Naked print() statements will fail CI pipeline checks.",
        "team": "ALL",
        "access_level": "employee",
        "effective_date": "2026-09-01",
        "highlight_tag": "Active CI Gate",
        "gcs_uri": "gs://company-knowledge-mesh/engineering/logging_standards_2026.md",
        "action_suggestion": "Check your repository logging wrapper against Code Mentor standards.",
        "full_content": (
            "### Mandatory Structured JSON Logging Standards (RFC-5424)\n\n"
            "**Policy Status**: Active Enforcement across all microservices.\n\n"
            "**Key Requirements**:\n"
            "- Never commit raw `print(...)` in Python or `console.log(...)` in TypeScript.\n"
            "- Structured logs must include `event`, `trace_id`, `user_id`, and `severity`.\n"
            "- Trace context correlates logs directly with Google Cloud Trace and BigQuery telemetry.\n\n"
            "**Example Implementation (Python)**:\n"
            "```python\n"
            "import logging, json\n"
            "logger = logging.getLogger('payments-service')\n"
            "logger.info(json.dumps({\n"
            "    'event': 'PAYMENT_PROCESSED',\n"
            "    'trace_id': trace_id,\n"
            "    'amount_cents': 2500,\n"
            "    'status': 'SUCCESS'\n"
            "}))\n"
            "```"
        )
    },
    {
        "insight_id": "INSIGHT-2026-002",
        "doc_id": "DOC-PLT-001",
        "title": "Cloud SQL Auth Proxy v2.1 Sidecar Requirement",
        "category": "RUNBOOK",
        "summary": "Direct PostgreSQL connections from GKE pods without the Cloud SQL Auth Proxy sidecar are deprecated as of Q3. Workload Identity is now required.",
        "team": "Platform",
        "access_level": "employee",
        "effective_date": "2026-08-28",
        "highlight_tag": "Infrastructure Notice",
        "gcs_uri": "gs://company-knowledge-mesh/platform/kubernetes_cluster_triage.md",
        "action_suggestion": "Review the Kubernetes cluster triage and proxy sidecar runbook.",
        "full_content": (
            "### Cloud SQL Auth Proxy Sidecar Configuration & Triage\n\n"
            "**Scope**: All GKE workloads connecting to Cloud SQL PostgreSQL.\n\n"
            "**Guidelines**:\n"
            "1. **Local Address**: Pods must route database queries to `127.0.0.1:5432`.\n"
            "2. **Workload Identity**: Authenticates pod service account with Google Cloud IAM without hardcoded passwords.\n"
            "3. **Triage Command**:\n"
            "   `kubectl logs <pod-name> -c cloud-sql-proxy -n staging`\n"
            "4. **Emergency Escalation**: Page on-call infrastructure engineers on `#help-infrastructure`."
        )
    },
    {
        "insight_id": "INSIGHT-2026-003",
        "doc_id": "DOC-PAY-001",
        "title": "Double-Entry Ledger Idempotency Key Specification",
        "category": "BLUEPRINT",
        "summary": "Payments Guild has updated the idempotency window to 24 hours on Redis KV cluster with automated BigQuery reconciliation streaming.",
        "team": "Payments",
        "access_level": "employee",
        "effective_date": "2026-09-04",
        "highlight_tag": "Payments Guild",
        "gcs_uri": "gs://company-knowledge-mesh/payments/architecture_overview_2026.md",
        "action_suggestion": "Inspect the Idempotency-Key headers in payment request routes.",
        "full_content": (
            "### Double-Entry Ledger & Idempotency Header Architecture\n\n"
            "**Overview**: High-throughput transaction processing for payments.\n\n"
            "**Protocol Rules**:\n"
            "- Every mutative endpoint requires an `Idempotency-Key: <UUID-v4>` header.\n"
            "- Redis cluster enforces a strict 24-hour cache TTL to avoid double-charging.\n"
            "- Transactions persist immutably to Cloud SQL PostgreSQL and stream via CDC to BigQuery audit tables.\n"
            "- Retry requests with the same key safely return the previously computed receipt."
        )
    },
    {
        "insight_id": "INSIGHT-2026-004",
        "doc_id": "DOC-ALL-001",
        "title": "Core Flexible Working Hours & Timesheet Finalization",
        "category": "POLICY",
        "summary": "Core collaboration hours are 10:00 AM - 4:00 PM local time. All weekly timesheets must be submitted by Friday 5:00 PM to ensure payroll accuracy.",
        "team": "ALL",
        "access_level": "employee",
        "effective_date": "2026-09-01",
        "highlight_tag": "People Ops Update",
        "gcs_uri": "gs://company-knowledge-mesh/company/code_of_conduct_2026.md",
        "action_suggestion": "Verify your current weekly timesheet status before end-of-week.",
        "full_content": (
            "### Workplace Flexibility & Weekly Timesheet Submission\n\n"
            "**Working Hours Guideline**:\n"
            "- Core collaboration window: 10:00 AM – 4:00 PM in your regional time zone.\n"
            "- Team members can arrange flexible schedules outside core hours in coordination with their manager.\n\n"
            "**Timesheet Deadlines**:\n"
            "- Weekly timesheets must be submitted by **Friday 5:00 PM**.\n"
            "- Ensure all project and training hours are accurately accounted for.\n"
            "- For questions, email `people-ops@company.com` or use the Timesheet Status action."
        )
    },
    {
        "insight_id": "INSIGHT-2026-005",
        "doc_id": "DOC-MGR-001",
        "title": "Q4 Performance Calibration & Compensation Review Cycle",
        "category": "POLICY",
        "summary": "Managers must complete peer review syntheses and submit promotion calibration packages by October 15th for department review.",
        "team": "ALL",
        "access_level": "manager",
        "effective_date": "2026-09-05",
        "highlight_tag": "Confidential - Manager / HR",
        "gcs_uri": "gs://company-knowledge-mesh/hr/compensation_guidelines_2026.pdf",
        "action_suggestion": "Review managerial compensation bands and calibration schedules.",
        "full_content": (
            "### Q4 Managerial Calibration & Promotion Review Guidelines\n\n"
            "*(Restricted to Managers and People Operations Partners)*\n\n"
            "**Timeline & Action Milestones**:\n"
            "- September 15 – October 5: Self and peer review window.\n"
            "- October 15: Manager evaluation forms due.\n"
            "- October 20 – 28: Cross-functional calibration panels.\n"
            "- November 15: Annual merit adjustment and equity refresh distribution.\n\n"
            "**Promotion Requirements**:\n"
            "- Two senior peer reviews demonstrating sustained impact at the next career level."
        )
    },
]
