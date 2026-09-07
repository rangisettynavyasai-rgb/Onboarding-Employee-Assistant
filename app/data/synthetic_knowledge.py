"""
Synthetic Knowledge Catalog & Asset Dataset.
Represents GCS-backed documents with metadata and pre-retrieval ACL boundaries.
"""

from typing import Dict, List
from app.models import KnowledgeAsset, KnowledgeChunk, AccessLevel


SYNTHETIC_KNOWLEDGE_CATALOG: Dict[str, KnowledgeAsset] = {
    # 1. Company-wide: Code of Conduct (Accessible to all employees)
    "DOC-ALL-001": KnowledgeAsset(
        document_id="DOC-ALL-001",
        title="Patchamomma 2026 Code of Conduct & Values",
        source="People Operations",
        gcs_uri="gs://patchamomma-knowledge-mesh/company/code_of_conduct_2026.md",
        team="ALL",
        access_level=AccessLevel.EMPLOYEE,
        document_type="POLICY",
        owner="amanda.w@company.com",
        description="Core company values, inclusive culture, and workplace ethics.",
        chunks=[
            KnowledgeChunk(
                chunk_id="CHK-ALL-001-1",
                document_id="DOC-ALL-001",
                chunk_index=0,
                content=(
                    "# Patchamomma 2026 Code of Conduct\n"
                    "We prioritize psychological safety, radical candor with empathy, and customer obsession.\n"
                    "Working hours are core-flexible (10am - 4pm local). Timesheets must be finalized by Friday 5pm."
                ),
                team="ALL",
                access_level=AccessLevel.EMPLOYEE,
            )
        ],
    ),

    # 2. Company-wide: Corporate Logging & Coding Standards (Accessible to all employees)
    "DOC-ALL-002": KnowledgeAsset(
        document_id="DOC-ALL-002",
        title="Enterprise Python & Structured Logging Standards",
        source="Architecture Guild",
        gcs_uri="gs://patchamomma-knowledge-mesh/engineering/logging_standards_2026.md",
        team="ALL",
        access_level=AccessLevel.EMPLOYEE,
        document_type="STANDARDS",
        owner="priya.nair@company.com",
        description="Requirements for structured JSON logging and naked exception handling.",
        chunks=[
            KnowledgeChunk(
                chunk_id="CHK-ALL-002-1",
                document_id="DOC-ALL-002",
                chunk_index=0,
                content=(
                    "# Corporate Coding Standards 2026\n"
                    "1. Never use raw print(...) statements in production services. Always use logger.info(json.dumps(...)).\n"
                    "2. All microservices communicate via Cloud Pub/Sub and Cloud SQL Postgres proxy with IAM auth.\n"
                    "3. Functions must be fully type-hinted and pass ruff/mypy checks."
                ),
                team="ALL",
                access_level=AccessLevel.EMPLOYEE,
            )
        ],
    ),

    # 3. Payments Team Only: Architecture Blueprint
    "DOC-PAY-001": KnowledgeAsset(
        document_id="DOC-PAY-001",
        title="Payments Microservice Architecture & Event Ledger Blueprint",
        source="Payments Architecture",
        gcs_uri="gs://patchamomma-knowledge-mesh/engineering/payments/architecture_blueprint.pdf",
        team="Payments",
        access_level=AccessLevel.EMPLOYEE,
        document_type="ARCHITECTURE_SPEC",
        owner="priya.nair@company.com",
        description="Confidential Payments transaction flow, idempotency keys, and database topology.",
        chunks=[
            KnowledgeChunk(
                chunk_id="CHK-PAY-001-1",
                document_id="DOC-PAY-001",
                chunk_index=0,
                content=(
                    "# Payments Architecture Blueprint\n"
                    "The Payments Gateway utilizes an event-sourced ledger on Cloud SQL PostgreSQL with read-replicas.\n"
                    "Transactions require an Idempotency-Key header. Staging database URL is managed via Cloud SQL Proxy at 127.0.0.1:5432.\n"
                    "Video walkthrough: `gs://patchamomma-knowledge-mesh/videos/onboarding/payments_deepdive.mp4` (Key timestamp: 18:45 for Cloud SQL Proxy setup)."
                ),
                team="Payments",
                access_level=AccessLevel.EMPLOYEE,
            )
        ],
    ),

    # 4. Platform Team Only: Kubernetes Cluster Triage Runbook
    "DOC-PLT-001": KnowledgeAsset(
        document_id="DOC-PLT-001",
        title="Platform Kubernetes (GKE) Cluster Triage & Pod Recovery Runbook",
        source="Platform Infrastructure",
        gcs_uri="gs://patchamomma-knowledge-mesh/runbooks/kubernetes_cluster_triage.md",
        team="Platform",
        access_level=AccessLevel.EMPLOYEE,
        document_type="RUNBOOK",
        owner="alex.chen@company.com",
        description="Triage runbook for GKE cluster autoscaling, node repair, and CrashLoopBackOff.",
        chunks=[
            KnowledgeChunk(
                chunk_id="CHK-PLT-001-1",
                document_id="DOC-PLT-001",
                chunk_index=0,
                content=(
                    "# GKE Cluster Triage Runbook\n"
                    "For Pod CrashLoopBackOff events, execute `kubectl logs --tail=100 -n production`.\n"
                    "If nodes are non-responsive, verify Cloud NAT and VPC firewall rules before restarting node pools."
                ),
                team="Platform",
                access_level=AccessLevel.EMPLOYEE,
            )
        ],
    ),

    # 5. Manager Role Only: 1:1 Cadence & Performance Reviews
    "DOC-MGR-001": KnowledgeAsset(
        document_id="DOC-MGR-001",
        title="Manager Onboarding & Performance Review Playbook",
        source="Leadership Development",
        gcs_uri="gs://patchamomma-knowledge-mesh/management/manager_playbook_2026.md",
        team="ALL",
        access_level=AccessLevel.MANAGER,
        document_type="CONFIDENTIAL_GUIDE",
        owner="sarah.j@company.com",
        description="Confidential guide for managers on conducting onboarding check-ins and performance scoring.",
        chunks=[
            KnowledgeChunk(
                chunk_id="CHK-MGR-001-1",
                document_id="DOC-MGR-001",
                chunk_index=0,
                content=(
                    "# Engineering Manager Playbook (Manager Eyes Only)\n"
                    "Hold weekly 30-minute 1:1s with all new joiners throughout their first 90 days.\n"
                    "Review timesheet submissions every Friday afternoon in the Manager Portal."
                ),
                team="ALL",
                access_level=AccessLevel.MANAGER,
            )
        ],
    ),

    # 6. HR Role Only: Compensation Bands & Offboarding Protocols
    "DOC-HR-001": KnowledgeAsset(
        document_id="DOC-HR-001",
        title="HR Compensation Bands & Confidential People Operations Manual",
        source="People Operations",
        gcs_uri="gs://patchamomma-knowledge-mesh/hr/compensation_bands_2026.pdf",
        team="HR",
        access_level=AccessLevel.HR,
        document_type="RESTRICTED_POLICY",
        owner="amanda.w@company.com",
        description="Restricted HR compensation matrices and equity grant guidelines.",
        chunks=[
            KnowledgeChunk(
                chunk_id="CHK-HR-001-1",
                document_id="DOC-HR-001",
                chunk_index=0,
                content=(
                    "# HR Restricted Salary & Equity Matrix\n"
                    "Level L3 (SWE I): Base range $130,000 - $160,000.\n"
                    "Level L4 (SWE II): Base range $160,000 - $195,000.\n"
                    "Level L6 (Staff): Base range $230,000 - $280,000."
                ),
                team="HR",
                access_level=AccessLevel.HR,
            )
        ],
    ),

    # 7. IT Role Only: IAM Key Rotation & Firewall Administration Manual
    "DOC-IT-001": KnowledgeAsset(
        document_id="DOC-IT-001",
        title="Corporate IT Security & IAM Master Key Vault Administration",
        source="IT Operations",
        gcs_uri="gs://patchamomma-knowledge-mesh/it/iam_firewall_admin.md",
        team="IT",
        access_level=AccessLevel.IT,
        document_type="RESTRICTED_MANUAL",
        owner="marcus.v@company.com",
        description="Master runbook for provisioning employee VPN certificates and rotation of GCP KMS keys.",
        chunks=[
            KnowledgeChunk(
                chunk_id="CHK-IT-001-1",
                document_id="DOC-IT-001",
                chunk_index=0,
                content=(
                    "# IT Master Administration & KMS Key Vault\n"
                    "VPN certificates must be issued using Cloud KMS HSM keys.\n"
                    "Revoke compromised service account keys immediately via `gcloud iam service-accounts keys delete`."
                ),
                team="IT",
                access_level=AccessLevel.IT,
            )
        ],
    ),
}
