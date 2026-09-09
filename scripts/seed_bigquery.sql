-- BigQuery DDL and Seed Data for Employee Assistant System of Record
-- Target Project: patchamomma-505416
-- Target Dataset: employee_ai

CREATE TABLE IF NOT EXISTS `patchamomma-505416.employee_ai.employees` (
  employee_id STRING NOT NULL,
  google_subject STRING,
  email STRING NOT NULL,
  name STRING NOT NULL,
  department STRING,
  team STRING,
  job_role STRING,
  authorization_role STRING,
  manager_id STRING,
  location STRING,
  joining_date DATE,
  onboarding_status STRING,
  is_day_one BOOL,
  assigned_buddy_name STRING,
  assigned_buddy_email STRING,
  onboarding_track STRING
);

CREATE TABLE IF NOT EXISTS `patchamomma-505416.employee_ai.onboarding_tasks` (
  task_id STRING NOT NULL,
  employee_id STRING NOT NULL,
  title STRING NOT NULL,
  description STRING,
  status STRING,
  due_days_after_start INT64,
  due_date STRING,
  completed_at TIMESTAMP,
  category STRING,
  action_link STRING
);

-- Seed Employees
MERGE INTO `patchamomma-505416.employee_ai.employees` T
USING (
  SELECT
    'EMP-2026-001' AS employee_id,
    'sub_google_2026_001' AS google_subject,
    'navyasai.r17@iiits.in' AS email,
    'Navya Rangisetty' AS name,
    'Engineering' AS department,
    'Payments' AS team,
    'Software Engineer' AS job_role,
    'employee' AS authorization_role,
    'EMP-2026-003' AS manager_id,
    'HQ' AS location,
    DATE '2026-09-01' AS joining_date,
    'IN_PROGRESS' AS onboarding_status,
    TRUE AS is_day_one,
    'Priya Nair' AS assigned_buddy_name,
    'priya.nair@company.com' AS assigned_buddy_email,
    'Payments Engineering' AS onboarding_track
  UNION ALL
  SELECT
    'EMP-2026-002',
    'sub_google_2026_002',
    'marcus.v@company.com',
    'Marcus Vance',
    'Engineering',
    'Platform Infrastructure',
    'Senior DevOps Engineer',
    'it',
    'EMP-2026-003',
    'HQ',
    DATE '2026-08-15',
    'IN_PROGRESS',
    FALSE,
    'David Miller',
    'david.miller@company.com',
    'Cloud Platform & Security'
  UNION ALL
  SELECT
    'EMP-2026-003',
    'sub_google_2026_003',
    'sarah.jenkins@company.com',
    'Sarah Jenkins',
    'Engineering',
    'Payments',
    'Engineering Manager',
    'manager',
    NULL,
    'HQ',
    DATE '2024-03-01',
    'COMPLETED',
    FALSE,
    NULL,
    NULL,
    'Leadership'
  UNION ALL
  SELECT
    'EMP-2026-009',
    'sub_google_2026_009',
    'amanda.walker@company.com',
    'Amanda Walker',
    'People Operations',
    'People Operations',
    'HR Specialist',
    'hr',
    NULL,
    'HQ',
    DATE '2024-01-10',
    'COMPLETED',
    FALSE,
    NULL,
    NULL,
    'People Operations'
) S
ON T.employee_id = S.employee_id
WHEN MATCHED THEN
  UPDATE SET
    google_subject = S.google_subject,
    email = S.email,
    name = S.name,
    department = S.department,
    team = S.team,
    job_role = S.job_role,
    authorization_role = S.authorization_role,
    manager_id = S.manager_id,
    location = S.location,
    joining_date = S.joining_date,
    onboarding_status = S.onboarding_status,
    is_day_one = S.is_day_one,
    assigned_buddy_name = S.assigned_buddy_name,
    assigned_buddy_email = S.assigned_buddy_email,
    onboarding_track = S.onboarding_track
WHEN NOT MATCHED THEN
  INSERT (employee_id, google_subject, email, name, department, team, job_role, authorization_role, manager_id, location, joining_date, onboarding_status, is_day_one, assigned_buddy_name, assigned_buddy_email, onboarding_track)
  VALUES (S.employee_id, S.google_subject, S.email, S.name, S.department, S.team, S.job_role, S.authorization_role, S.manager_id, S.location, S.joining_date, S.onboarding_status, S.is_day_one, S.assigned_buddy_name, S.assigned_buddy_email, S.onboarding_track);

-- Seed Initial Tasks for EMP-2026-001
MERGE INTO `patchamomma-505416.employee_ai.onboarding_tasks` T
USING (
  SELECT 'TASK-001-SEC' AS task_id, 'EMP-2026-001' AS employee_id, 'Complete Corporate Security & Data Privacy Training' AS title, 'Complete mandatory security training, compliance acknowledgment, and IAM zero-trust overview.' AS description, 'PENDING' AS status, 1 AS due_days_after_start, 'Security & Compliance' AS category, 'https://learning.internal.company.com/courses/sec-2026' AS action_link
  UNION ALL
  SELECT 'TASK-001-ENV', 'EMP-2026-001', 'Set up Local Dev Environment & Cloud SQL Auth Proxy', 'Clone payment microservice repos, install docker-compose, and configure Cloud SQL Auth Proxy sidecar via 127.0.0.1:5432.', 'PENDING', 2, 'Development Setup', 'gs://patchamomma-505416-employee-ai-knowledge/architecture_overview_2026.md'
  UNION ALL
  SELECT 'TASK-001-BUDDY', 'EMP-2026-001', 'Schedule 1:1 Intro with Onboarding Buddy (Priya Nair)', 'Meet with your assigned buddy for architecture walkthrough and team sync.', 'PENDING', 3, 'Team Integration', 'mailto:priya.nair@company.com'
  UNION ALL
  SELECT 'TASK-001-GIT', 'EMP-2026-001', 'Submit First Sandbox Pull Request to payments-core', 'Open a small PR verifying Conventional Commits and RFC-5424 structured logging adherence.', 'PENDING', 5, 'Engineering Standards', 'https://github.company.internal/payments/payments-core/pulls'
  UNION ALL
  SELECT 'TASK-001-BEN', 'EMP-2026-001', 'Enroll in Health, Dental & 401(k) Retirement Benefits', 'Select healthcare tier and 401(k) retirement plan contribution percentage via HR portal.', 'PENDING', 7, 'Benefits & HR', 'https://hr.internal.company.com/benefits'
  UNION ALL
  SELECT 'TASK-001-TIME', 'EMP-2026-001', 'Log Week 1 Timesheet Before Friday 5:00 PM Deadline', 'Review first-week hours and finalize weekly submission before Friday 5:00 PM cut-off.', 'PENDING', 5, 'Operations & Payroll', 'https://timesheets.internal.company.com'
) S
ON T.task_id = S.task_id AND T.employee_id = S.employee_id
WHEN MATCHED THEN
  UPDATE SET title = S.title, description = S.description, status = S.status, due_days_after_start = S.due_days_after_start, category = S.category, action_link = S.action_link
WHEN NOT MATCHED THEN
  INSERT (task_id, employee_id, title, description, status, due_days_after_start, category, action_link)
  VALUES (S.task_id, S.employee_id, S.title, S.description, S.status, S.due_days_after_start, S.category, S.action_link);
