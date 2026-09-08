-- ============================================================================
-- Company AI Assistant: BigQuery Synthetic Seed Data
-- Target Dataset: employee_ai
-- ============================================================================

-- 1. Seed Employees
INSERT INTO `patchamomma-505416.employee_ai.employees`
(employee_id, google_subject, email, name, department, team, job_role, authorization_role, manager_id, location, joining_date, onboarding_status, is_day_one, assigned_buddy_name, assigned_buddy_email, onboarding_track)
VALUES
('EMP-2026-001', 'google-sub-rahul-001', 'rahul.sharma@company.com', 'Rahul Sharma', 'Engineering', 'Payments', 'Software Engineer I', 'employee', 'EMP-2026-010', 'Seattle, WA', '2026-09-01', 'IN_PROGRESS', TRUE, 'Priya Nair', 'priya.nair@company.com', 'Backend'),
('EMP-2026-002', 'google-sub-maya-002', 'maya.lin@company.com', 'Maya Lin', 'Infrastructure', 'Platform', 'Cloud Infrastructure Intern', 'employee', 'EMP-2026-005', 'San Francisco, CA', '2026-09-01', 'IN_PROGRESS', TRUE, 'David Miller', 'david.miller@company.com', 'Platform'),
('EMP-2026-003', 'google-sub-liam-003', 'liam.vance@company.com', 'Liam Vance', 'Engineering', 'Payments', 'Software Engineer II', 'employee', 'EMP-2026-010', 'Austin, TX', '2026-08-15', 'IN_PROGRESS', FALSE, 'Priya Nair', 'priya.nair@company.com', 'Backend'),
('EMP-2026-004', 'google-sub-carlos-004', 'carlos.s@company.com', 'Carlos Santana', 'Data Platforms', 'DataOps', 'Senior Staff Data Engineer', 'employee', 'EMP-2026-005', 'New York, NY', '2024-05-10', 'COMPLETED', FALSE, NULL, NULL, 'DataOps'),
('EMP-2026-005', 'google-sub-alex-005', 'alex.chen@company.com', 'Alex Chen', 'Infrastructure', 'Platform', 'Director of Platform Engineering', 'manager', NULL, 'San Francisco, CA', '2023-01-15', 'COMPLETED', FALSE, NULL, NULL, 'Platform'),
('EMP-2026-006', 'google-sub-priya-006', 'priya.nair@company.com', 'Priya Nair', 'Engineering', 'Payments', 'Staff Software Engineer & Tech Lead', 'employee', 'EMP-2026-010', 'Seattle, WA', '2023-08-01', 'COMPLETED', FALSE, NULL, NULL, 'Backend'),
('EMP-2026-007', 'google-sub-elena-007', 'elena.r@company.com', 'Elena Rostova', 'Security', 'Platform', 'Senior SecOps & Cloud IAM Engineer', 'employee', 'EMP-2026-005', 'Boston, MA', '2024-01-10', 'COMPLETED', FALSE, NULL, NULL, 'Platform'),
('EMP-2026-008', 'google-sub-marcus-008', 'marcus.v@company.com', 'Marcus Vance', 'IT Services', 'IT', 'Lead IT Systems Administrator', 'it', NULL, 'Chicago, IL', '2023-11-01', 'COMPLETED', FALSE, NULL, NULL, 'General'),
('EMP-2026-009', 'google-sub-amanda-009', 'amanda.w@company.com', 'Amanda Walker', 'People Operations', 'HR', 'Senior People Ops Specialist', 'hr', NULL, 'New York, NY', '2023-04-15', 'COMPLETED', FALSE, NULL, NULL, 'General'),
('EMP-2026-010', 'google-sub-sarah-010', 'sarah.j@company.com', 'Sarah Jenkins', 'Engineering', 'Payments', 'Engineering Manager - Payments', 'manager', NULL, 'Seattle, WA', '2022-09-01', 'COMPLETED', FALSE, NULL, NULL, 'Backend');

-- 2. Seed Onboarding Tasks
INSERT INTO `patchamomma-505416.employee_ai.employee_onboarding_tasks`
(task_id, employee_id, title, description, status, due_days_after_start, completed_at, category, action_link)
VALUES
('TASK-001-SEC', 'EMP-2026-001', 'Complete Corporate Security & Data Privacy Training', 'Review security policies, 2FA setup, and complete compliance module.', 'COMPLETED', 1, CURRENT_TIMESTAMP(), 'Security & Compliance', 'https://learning.internal.company.com/courses/sec-2026'),
('TASK-001-ENV', 'EMP-2026-001', 'Set up Local Dev Environment & Cloud SQL Proxy', 'Install gcloud CLI, Docker, and configure Cloud SQL Auth Proxy for PostgreSQL staging.', 'PENDING', 2, NULL, 'Development Setup', 'gs://patchamomma-505416-employee-ai-knowledge/runbooks/kubernetes_cluster_triage.md'),
('TASK-001-BUDDY', 'EMP-2026-001', 'Schedule 1:1 Intro with Onboarding Buddy (Priya Nair)', 'Connect with Priya for payments architecture overview and team introduction.', 'PENDING', 3, NULL, 'Team Integration', 'mailto:priya.nair@company.com'),
('TASK-001-GIT', 'EMP-2026-001', 'Submit first sandbox PR to payments-core repo', 'Clone repository, make standard JSON logger improvement, and open test PR.', 'PENDING', 5, NULL, 'First Milestone', 'https://github.com/company/payments-core'),
('TASK-002-SEC', 'EMP-2026-002', 'Complete Corporate Security & Data Privacy Training', 'Complete mandatory security basics and IAM access policies.', 'PENDING', 1, NULL, 'Security & Compliance', 'https://learning.internal.company.com/courses/sec-2026'),
('TASK-002-GCP', 'EMP-2026-002', 'Configure Google Cloud SDK & GKE Cluster Access', 'Set up gcloud auth and kubectl credentials for staging Kubernetes clusters.', 'PENDING', 2, NULL, 'Infrastructure Setup', 'gs://patchamomma-505416-employee-ai-knowledge/runbooks/kubernetes_cluster_triage.md');

-- 3. Seed Knowledge Assets
INSERT INTO `patchamomma-505416.employee_ai.knowledge_assets`
(document_id, title, source, gcs_uri, team, access_level, document_type, owner, description, created_at, updated_at)
VALUES
('DOC-ALL-001', 'Company Code of Conduct & Values', 'People Operations', 'gs://company-internal-knowledge/company/code_of_conduct_2026.md', 'ALL', 'employee', 'POLICY', 'amanda.w@company.com', 'Core company values, inclusive culture, and workplace ethics.', CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()),
('DOC-ALL-002', 'Enterprise Python & Structured Logging Standards', 'Architecture Guild', 'gs://patchamomma-505416-employee-ai-knowledge/engineering/logging_standards_2026.md', 'ALL', 'employee', 'STANDARDS', 'priya.nair@company.com', 'Requirements for structured JSON logging and naked exception handling.', CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()),
('DOC-PAY-001', 'Payments Microservice Architecture & Event Ledger Blueprint', 'Payments Architecture', 'gs://patchamomma-505416-employee-ai-knowledge/engineering/payments/architecture_blueprint.pdf', 'Payments', 'employee', 'ARCHITECTURE_SPEC', 'priya.nair@company.com', 'Confidential Payments transaction flow, idempotency keys, and database topology.', CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()),
('DOC-PLT-001', 'Platform Kubernetes (GKE) Cluster Triage & Pod Recovery Runbook', 'Platform Infrastructure', 'gs://patchamomma-505416-employee-ai-knowledge/runbooks/kubernetes_cluster_triage.md', 'Platform', 'employee', 'RUNBOOK', 'alex.chen@company.com', 'Triage runbook for GKE cluster autoscaling, node repair, and CrashLoopBackOff.', CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()),
('DOC-MGR-001', 'Manager Onboarding & Performance Review Playbook', 'Leadership Development', 'gs://patchamomma-505416-employee-ai-knowledge/management/manager_playbook_2026.md', 'ALL', 'manager', 'CONFIDENTIAL_GUIDE', 'sarah.j@company.com', 'Confidential guide for managers on conducting onboarding check-ins and performance scoring.', CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()),
('DOC-HR-001', 'HR Compensation Bands & Confidential People Operations Manual', 'People Operations', 'gs://patchamomma-505416-employee-ai-knowledge/hr/compensation_bands_2026.pdf', 'HR', 'hr', 'RESTRICTED_POLICY', 'amanda.w@company.com', 'Restricted HR compensation matrices and equity grant guidelines.', CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()),
('DOC-IT-001', 'Corporate IT Security & IAM Master Key Vault Administration', 'IT Operations', 'gs://patchamomma-505416-employee-ai-knowledge/it/iam_firewall_admin.md', 'IT', 'it', 'RESTRICTED_MANUAL', 'marcus.v@company.com', 'Master runbook for provisioning employee VPN certificates and rotation of GCP KMS keys.', CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP());

-- 4. Seed Knowledge Chunks
INSERT INTO `patchamomma-505416.employee_ai.knowledge_chunks`
(chunk_id, document_id, chunk_index, content, team, access_level)
VALUES
('CHK-ALL-001-1', 'DOC-ALL-001', 0, '# Company Code of Conduct\nWe prioritize psychological safety, radical candor with empathy, and customer obsession.\nWorking hours are core-flexible (10am - 4pm local). Timesheets must be finalized by Friday 5pm.', 'ALL', 'employee'),
('CHK-ALL-002-1', 'DOC-ALL-002', 0, '# Corporate Coding Standards 2026\n1. Never use raw print(...) statements in production services. Always use logger.info(json.dumps(...)).\n2. All microservices communicate via Cloud Pub/Sub and Cloud SQL Postgres proxy with IAM auth.\n3. Functions must be fully type-hinted and pass ruff/mypy checks.', 'ALL', 'employee'),
('CHK-PAY-001-1', 'DOC-PAY-001', 0, '# Payments Architecture Blueprint\nThe Payments Gateway utilizes an event-sourced ledger on Cloud SQL PostgreSQL with read-replicas.\nTransactions require an Idempotency-Key header. Staging database URL is managed via Cloud SQL Proxy at 127.0.0.1:5432.\nVideo walkthrough: `gs://patchamomma-505416-employee-ai-knowledge/videos/onboarding/payments_deepdive.mp4` (Key timestamp: 18:45 for Cloud SQL Proxy setup).', 'Payments', 'employee'),
('CHK-PLT-001-1', 'DOC-PLT-001', 0, '# GKE Cluster Triage Runbook\nFor Pod CrashLoopBackOff events, execute `kubectl logs --tail=100 -n production`.\nIf nodes are non-responsive, verify Cloud NAT and VPC firewall rules before restarting node pools.', 'Platform', 'employee'),
('CHK-MGR-001-1', 'DOC-MGR-001', 0, '# Engineering Manager Playbook (Manager Eyes Only)\nHold weekly 30-minute 1:1s with all new joiners throughout their first 90 days.\nReview timesheet submissions every Friday afternoon in the Manager Portal.', 'ALL', 'manager'),
('CHK-HR-001-1', 'DOC-HR-001', 0, '# HR Restricted Salary & Equity Matrix\nLevel L3 (SWE I): Base range $130,000 - $160,000.\nLevel L4 (SWE II): Base range $160,000 - $195,000.\nLevel L6 (Staff): Base range $230,000 - $280,000.', 'HR', 'hr'),
('CHK-IT-001-1', 'DOC-IT-001', 0, '# IT Master Administration & KMS Key Vault\nVPN certificates must be issued using Cloud KMS HSM keys.\nRevoke compromised service account keys immediately via `gcloud iam service-accounts keys delete`.', 'IT', 'it');

-- 5. Seed Timesheets
INSERT INTO `patchamomma-505416.employee_ai.timesheets`
(timesheet_id, employee_id, period_start, period_end, hours_logged, status, due_date)
VALUES
('TS-2026-W36-001', 'EMP-2026-001', '2026-08-31', '2026-09-04', 32.0, 'PENDING', '2026-09-04'),
('TS-2026-W36-002', 'EMP-2026-002', '2026-08-31', '2026-09-04', 40.0, 'SUBMITTED', '2026-09-04'),
('TS-2026-W35-003', 'EMP-2026-003', '2026-08-24', '2026-08-28', 0.0, 'OVERDUE', '2026-08-28'),
('TS-2026-W36-004', 'EMP-2026-004', '2026-08-31', '2026-09-04', 40.0, 'APPROVED', '2026-09-04');

-- 6. Seed Team Escalations
INSERT INTO `patchamomma-505416.employee_ai.team_directory_mesh`
(system_domain, primary_lead_name, primary_email, primary_on_vacation, backup_lead_name, backup_email, backup_on_vacation, general_team_channel)
VALUES
('Kubernetes', 'Alex Chen', 'alex.chen@company.com', FALSE, 'Sarah Connor', 'sarah.c@company.com', FALSE, '#k8s-platform-support'),
('Cloud SQL', 'David Miller', 'david.miller@company.com', TRUE, 'Priya Nair', 'priya.nair@company.com', FALSE, '#database-support-general'),
('IAM & Security', 'Elena Rostova', 'elena.r@company.com', TRUE, 'Marcus Vance', 'marcus.v@company.com', TRUE, '#secops-emergency-triage'),
('Data Pipelines', 'Sofia Patel', 'sofia.patel@company.com', FALSE, 'Jordan Lee', 'jordan.lee@company.com', TRUE, '#data-engineering-help');
