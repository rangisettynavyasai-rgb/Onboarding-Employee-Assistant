-- ============================================================================
-- Company AI Assistant: Master Unified Knowledge Mesh & Telemetry Schemas
-- Production BigQuery DDL for Cloud Run Enterprise Backend
-- Dataset: employee_ai
-- ============================================================================

-- Master Dataset
CREATE SCHEMA IF NOT EXISTS `patchamomma-505416.employee_ai`
OPTIONS (
  location = 'us-central1',
  description = 'Unified Knowledge Mesh, Employee Directory and Telemetry dataset'
);

-- ----------------------------------------------------------------------------
-- Table 1: Employees Directory (Identity Mapping & Governance)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE `patchamomma-505416.employee_ai.employees` (
    employee_id STRING NOT NULL OPTIONS(description="Internal Primary Key, e.g. EMP-2026-001"),
    google_subject STRING NOT NULL OPTIONS(description="Google Unique Subject ID (sub) claim"),
    email STRING NOT NULL,
    name STRING NOT NULL,
    department STRING NOT NULL,
    team STRING NOT NULL,
    job_role STRING NOT NULL,
    authorization_role STRING NOT NULL OPTIONS(description="employee, manager, hr, it"),
    manager_id STRING,
    location STRING NOT NULL,
    joining_date DATE NOT NULL,
    onboarding_status STRING NOT NULL OPTIONS(description="NOT_STARTED, IN_PROGRESS, COMPLETED"),
    is_day_one BOOLEAN NOT NULL,
    assigned_buddy_name STRING,
    assigned_buddy_email STRING,
    onboarding_track STRING NOT NULL OPTIONS(description="Backend, Platform, DataOps, General")
);

-- ----------------------------------------------------------------------------
-- Table 2: Employee Onboarding Tasks
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE `patchamomma-505416.employee_ai.employee_onboarding_tasks` (
    task_id STRING NOT NULL,
    employee_id STRING NOT NULL,
    title STRING NOT NULL,
    description STRING NOT NULL,
    status STRING NOT NULL OPTIONS(description="PENDING, IN_PROGRESS, COMPLETED, BLOCKED"),
    due_days_after_start INT64 NOT NULL,
    completed_at TIMESTAMP,
    category STRING NOT NULL,
    action_link STRING
);

-- ----------------------------------------------------------------------------
-- Table 3: Knowledge Assets & Mesh Catalog (Pre-Retrieval ACL Metadata)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE `patchamomma-505416.employee_ai.knowledge_assets` (
    document_id STRING NOT NULL,
    title STRING NOT NULL,
    source STRING NOT NULL,
    gcs_uri STRING NOT NULL,
    team STRING NOT NULL OPTIONS(description="Payments, Platform, HR, IT, ALL"),
    access_level STRING NOT NULL OPTIONS(description="employee, manager, hr, it"),
    document_type STRING NOT NULL,
    owner STRING NOT NULL,
    description STRING,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

-- ----------------------------------------------------------------------------
-- Table 4: Knowledge Chunks (Indexed Content & ACL Tags)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE `patchamomma-505416.employee_ai.knowledge_chunks` (
    chunk_id STRING NOT NULL,
    document_id STRING NOT NULL,
    chunk_index INT64 NOT NULL,
    content STRING NOT NULL,
    team STRING NOT NULL,
    access_level STRING NOT NULL
);

-- ----------------------------------------------------------------------------
-- Table 5: Timesheet Records
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE `patchamomma-505416.employee_ai.timesheets` (
    timesheet_id STRING NOT NULL,
    employee_id STRING NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    hours_logged FLOAT64 NOT NULL,
    status STRING NOT NULL OPTIONS(description="SUBMITTED, PENDING, OVERDUE, APPROVED"),
    due_date DATE NOT NULL
);

-- ----------------------------------------------------------------------------
-- Table 6: Incidents & Support Tickets
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE `patchamomma-505416.employee_ai.incidents` (
    incident_id STRING NOT NULL,
    created_by STRING NOT NULL,
    category STRING NOT NULL,
    summary STRING NOT NULL,
    severity STRING NOT NULL OPTIONS(description="LOW, MEDIUM, HIGH, CRITICAL"),
    status STRING NOT NULL,
    assigned_team STRING NOT NULL,
    created_at TIMESTAMP NOT NULL
);

-- ----------------------------------------------------------------------------
-- Table 7: Team Directory Mesh (Point-to-Person Escalation Matrix)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE `patchamomma-505416.employee_ai.team_directory_mesh` (
    system_domain STRING NOT NULL,
    primary_lead_name STRING NOT NULL,
    primary_email STRING NOT NULL,
    primary_on_vacation BOOLEAN NOT NULL,
    backup_lead_name STRING NOT NULL,
    backup_email STRING NOT NULL,
    backup_on_vacation BOOLEAN NOT NULL,
    general_team_channel STRING NOT NULL
);

-- ----------------------------------------------------------------------------
-- Table 8: Agent Telemetry & Friction Log (Looker Studio Streaming Feeds)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE `patchamomma-505416.employee_ai.agent_telemetry_friction_log` (
    log_id STRING NOT NULL,
    user_id STRING NOT NULL,
    user_role STRING NOT NULL,
    assigned_team STRING NOT NULL,
    query_timestamp TIMESTAMP NOT NULL,
    user_query_intent STRING NOT NULL,
    resolution_status STRING NOT NULL,
    friction_duration_minutes INT64 NOT NULL,
    blocker_severity STRING,
    metadata_json STRING
);

-- ----------------------------------------------------------------------------
-- Table 9: Employee ID Sequence
-- ----------------------------------------------------------------------------
-- The application uses this row as an atomic allocator for EMP-YYYY-NNN IDs.
-- It avoids MAX(employee_id)+1 races across horizontally scaled Cloud Run instances.
CREATE TABLE IF NOT EXISTS `patchamomma-505416.employee_ai.employee_id_sequences` (
    sequence_name STRING NOT NULL,
    id_year INT64 NOT NULL,
    next_sequence INT64 NOT NULL
);
