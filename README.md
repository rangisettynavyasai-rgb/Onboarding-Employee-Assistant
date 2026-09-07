# Patchamomma 2026: Enterprise AI Onboarding & Employee Assistant Framework

[![Node.js](https://img.shields.io/badge/Node.js-22_LTS-green.svg)](https://nodejs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-blue.svg)](https://www.typescriptlang.org/)
[![Google Cloud Run](https://img.shields.io/badge/Google%20Cloud-Cloud%20Run-blue.svg)](https://cloud.google.com/run)
[![BigQuery](https://img.shields.io/badge/GCP-BigQuery%20Knowledge%20Mesh-orange.svg)](https://cloud.google.com/bigquery)
[![Gemini 2.5 Flash](https://img.shields.io/badge/Google%20GenAI-Gemini%202.5%20Flash-purple.svg)](https://ai.google.dev/)

Production-grade **Multi-Agent Enterprise AI Assistant** built with **TypeScript**, **Node.js 22 LTS**, and **Express**, engineered for deployment to **Google Cloud Run**. The system integrates **Google Identity Services (GIS)**, **Gemini 2.5 Flash** (via `@google/genai`), a **BigQuery Knowledge Mesh**, and **Google Cloud Storage (GCS)** assets.

---

## 🏛️ System Architecture

```
                                [ Incoming User Request ]
                                           │
                                           ▼
                             ┌───────────────────────────┐
                             │ Google Identity (GIS/IAP) │ (Extracts verified sub & email)
                             └─────────────┬─────────────┘
                                           │ AuthenticatedPrincipal
                                           ▼
                             ┌───────────────────────────┐
                             │  Employee Identity Lookup │ (sub -> internal EmployeeRecord)
                             └─────────────┬─────────────┘
                                           │ EmployeeContext (Role, Team, Track, Clearance)
                                           ▼
                             ┌───────────────────────────┐
                             │    Session & Security     │ (Perimeter enforcement & session binding)
                             └─────────────┬─────────────┘
                                           │
                                           ▼
                             ┌───────────────────────────┐
                             │     Supervisor Agent      │ (Intent classification & LLM Orchestration)
                             └─────────────┬─────────────┘
                                           │
        ┌───────────────────┬──────────────┼───────────────────┬───────────────────┐
        ▼                   ▼              ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│  Onboarding   │   │  Operations   │ │   Knowledge   │ │  Code Mentor  │ │  Gemini 2.5   │
│  Specialist   │   │     Agent     │ │  Mesh Agent   │ │     Agent     │ │     Flash     │
└───────┬───────┘   └───────┬───────┘ └───────┬───────┘ └───────┬───────┘ └───────┬───────┘
        │                   │                 │                 │                 │
        ▼                   ▼                 ▼                 ▼                 ▼
 ┌─────────────┐     ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
 │ Day-1 Tasks │     │ Timesheets  │   │ Pre-Filter  │   │ JSON Logger │   │ Contextual  │
 │ & Checklists│     │ & Incident  │   │  ACL Mesh   │   │ & Cloud SQL │   │ Synthesis   │
 │   Rollup    │     │ Escalations │   │ (BQ + GCS)  │   │    Proxy    │   │  Responses  │
 └─────────────┘     └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘
```

---

## 🛡️ Core Security Boundaries

1. **Zero-Trust Token Identity**:
   - The frontend never submits `employee_id` in request payloads.
   - Authentication extracts the verified `sub` (Google Subject ID) or corporate email from the bearer token and resolves the trusted internal `EmployeeRecord`.
2. **Centralized Role-Based Access Control (RBAC)**:
   - Centralized authorization tags (`employee`, `manager`, `hr`, `it`) govern access to actions, data, and documents.
3. **Session Ownership Enforcement**:
   - Sessions are cryptographically and logically bound to `employee_id`. Cross-employee access attempts are rejected.
4. **Agent Tool Context Injection**:
   - Agent functions and tools do not accept `user_id` as an LLM argument; identity is always injected strictly from the authenticated server context.
5. **Pre-Retrieval Knowledge ACLs**:
   - Documents and chunks in the Knowledge Mesh are tagged with domain `team` (`Payments`, `Platform`, `HR`, `IT`, `ALL`) and `access_level` (`employee`, `manager`, `hr`, `it`).
   - Unauthorized chunks are filtered out **prior to retrieval** so sensitive data never enters the LLM context window.

---

## 🌐 The BigQuery Knowledge Mesh

### What is the Knowledge Mesh?
The **Knowledge Mesh** is an enterprise data and knowledge fabric that unifies internal documentation, architecture blueprints, standard operating procedures (SOPs), runbooks, policy guidelines, and video onboarding walkthroughs across **BigQuery** and **Google Cloud Storage (GCS)**.

Instead of a flat, unpartitioned vector store, the Knowledge Mesh applies domain-driven governance:
- **Domain Ownership**: Each knowledge asset is tagged with its owning team (`Payments`, `Platform`, `HR`, `IT`, `ALL`).
- **Clearance Level**: Assets specify clearance requirements (`employee`, `manager`, `hr`, `it`).
- **Pre-Retrieval Filtering**: When a user queries the Knowledge Mesh, the system filters candidates by the user's active team and clearance before passing context to Gemini.
- **Multimodal Video Deep Dive Mapping**: GCS video assets include indexed minute-and-second timestamps for high-friction onboarding milestones.

### BigQuery Schema Overview (`/bigquery/tables.sql`)

| Table Name | Description | Key Attributes |
| :--- | :--- | :--- |
| `employees` | Master employee identity directory | `employee_id`, `google_subject`, `email`, `team`, `job_role`, `authorization_role`, `onboarding_track` |
| `employee_onboarding_tasks` | Task checklists and completion records | `task_id`, `employee_id`, `title`, `status`, `due_days_after_start`, `action_link` |
| `knowledge_assets` | Catalog metadata for mesh documents & runbooks | `document_id`, `title`, `source`, `gcs_uri`, `team`, `access_level`, `document_type`, `owner` |
| `knowledge_chunks` | Searchable content chunks with ACL tags | `chunk_id`, `document_id`, `chunk_index`, `content`, `team`, `access_level` |
| `timesheets` | Weekly employee hours and approvals | `timesheet_id`, `employee_id`, `period_start`, `period_end`, `hours_logged`, `status` |
| `incidents` | IT / Platform tickets and outage reports | `incident_id`, `created_by`, `category`, `severity`, `status`, `assigned_team` |
| `team_directory_mesh` | 3-tier point-to-person escalation contacts | `system_domain`, `primary_lead_name`, `primary_on_vacation`, `backup_lead_name`, `general_team_channel` |
| `agent_telemetry_friction_log` | Streaming audit log for Looker Studio | `log_id`, `user_id`, `user_query_intent`, `resolution_status`, `friction_duration_minutes` |

---

## 📖 How-To Guides

### 1. How to Initialize BigQuery Tables
Execute the DDL script against your Google Cloud BigQuery dataset:

```bash
# Set your target GCP Project ID
export GCP_PROJECT_ID="your-gcp-project-id"

# Run DDL schema creation
bq query --use_legacy_sql=false < bigquery/tables.sql
```

### 2. How to Seed Synthetic Data
Populate the BigQuery tables with realistic multi-role corporate records:

```bash
bq query --use_legacy_sql=false < bigquery/seed_data.sql
```

### 3. How to Ingest New Documents into the Knowledge Mesh
To add a new document or runbook to the Knowledge Mesh:

1. **Upload the Asset to GCS**:
   ```bash
   gcloud storage cp docs/payments_runbook_2026.md gs://your-knowledge-bucket/engineering/payments/
   ```

2. **Register the Asset in `knowledge_assets`**:
   ```sql
   INSERT INTO `your-project.employee_ai.knowledge_assets`
   (document_id, title, source, gcs_uri, team, access_level, document_type, owner, description, created_at, updated_at)
   VALUES
   ('DOC-PAY-002', 'Payments Settlement Runbook', 'Payments Guild',
    'gs://your-knowledge-bucket/engineering/payments/payments_runbook_2026.md',
    'Payments', 'employee', 'RUNBOOK', 'priya.nair@company.com',
    'Reconciliation and settlement ledger procedures', CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP());
   ```

3. **Insert Searchable Chunks into `knowledge_chunks`**:
   ```sql
   INSERT INTO `your-project.employee_ai.knowledge_chunks`
   (chunk_id, document_id, chunk_index, content, team, access_level)
   VALUES
   ('CHK-PAY-002-1', 'DOC-PAY-002', 0,
    '# Settlement Procedures: Daily batch settles at 23:00 UTC via Cloud Tasks into BigQuery.',
    'Payments', 'employee');
   ```

### 4. How to Run Locally

```bash
# 1. Install dependencies
npm install

# 2. Configure environment variables (.env)
cp .env.example .env
# Edit .env and supply your GEMINI_API_KEY (optional for local mock mode)

# 3. Start development server with TypeScript watch mode
npm run dev

# 4. Or build and start production bundle
npm run build
npm start
```
The server will start at `http://localhost:3000`.

---

## 👥 Personas & Testing Scenarios

Use the built-in Persona Switcher on the login screen to test role-specific scenarios:

| Employee ID | Name | Role | Team | Authorization | Testing Scenario |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `EMP-2026-001` | **Rahul Sharma** | SWE I | Payments | `employee` | **Day-1 Onboarding**: Interactive checklist, buddy intro (`Priya Nair`), Cloud SQL proxy setup, video timestamp markers (04:15 & 18:45). |
| `EMP-2026-002` | **Maya Lin** | Intern | Platform | `employee` | **Day-1 Intern**: GKE cluster credentials, security training milestone. |
| `EMP-2026-003` | **Liam Vance** | SWE II | Payments | `employee` | **Operations**: Overdue timesheet reminder, sandbox PR submission. |
| `EMP-2026-005` | **Alex Chen** | Director | Platform | `manager` | **Escalation & Leadership**: Cloud SQL primary on-call point of contact. |
| `EMP-2026-009` | **Amanda Walker** | Senior Specialist | HR | `hr` | **HR Clearance**: Access to confidential salary & equity matrices and performance review playbooks. |
| `EMP-2026-010` | **Sarah Jenkins** | Manager | Payments | `manager` | **Manager Rollup**: Queries team onboarding progress across direct reports. |

---

## 🤖 Multi-Agent Specialization

| Agent | Trigger Patterns | Purpose & Deliverables |
| :--- | :--- | :--- |
| **Supervisor Agent** | All inbound requests | Master coordinator: parses intent, evaluates security perimeter, invokes Gemini 2.5 Flash for synthesis, or delegates to sub-agents. |
| **Onboarding Specialist** | `checklist`, `tasks`, `buddy`, `day 1`, `team progress` | Day-1 progress tracking, task completion (`/complete-task`), team rollups for managers. |
| **Operations Agent** | `timesheet`, `hours`, `lead`, `escalation`, `incident`, `ticket` | Timesheet status lookup, 3-tier point-to-person lead routing with vacation fallbacks, IT ticket creation. |
| **Knowledge Mesh Agent** | `doc`, `runbook`, `manual`, `policy`, `search`, `architecture` | Pre-retrieval ACL filtering across company standards, runbooks, and team blueprints. |
| **Code Mentor Agent** | `code`, `log`, `print`, `lint`, `standard`, `proxy` | Enforces zero raw print statement policy, structured JSON logging with correlation IDs, and Cloud SQL Auth Proxy standards. |

---

## ☁️ Google Cloud Run Deployment Guide (Option A: Secret Manager Injection)

This step-by-step deployment guide uses **Google Cloud Secret Manager** with **Cloud Run native secret injection (Option A)**. Your `GEMINI_API_KEY` is securely fetched from Secret Manager by Cloud Run at container startup and injected directly into `process.env.GEMINI_API_KEY`, keeping all credentials out of code and build artifacts.

---

### Step 1: Set Up Shell Environment & Project Variables

Open your terminal or Google Cloud Shell and set your configuration variables:

```bash
# Set your target Google Cloud Project ID and Region
export GCP_PROJECT_ID="your-gcp-project-id"
export GCP_REGION="us-central1"
export SERVICE_NAME="onboarding-assistant"
export ARTIFACT_REPO="patchamomma-repo"

# Set active project
gcloud config set project ${GCP_PROJECT_ID}
```

---

### Step 2: Enable Required Google Cloud APIs

Ensure the necessary services are enabled on your Google Cloud Project:

```bash
gcloud services enable \
  run.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com
```

---

### Step 3: Store Gemini API Key in Google Cloud Secret Manager

Create the secret named `gemini-api-key` and upload your key as the initial version:

```bash
# 1. Create the secret container in Secret Manager
gcloud secrets create gemini-api-key \
  --replication-policy="automatic"

# 2. Add your Gemini API key value (replace with your actual Gemini API key)
echo -n "AIzaSyYourActualGeminiAPIKeyHere" | gcloud secrets versions add gemini-api-key --data-file=-
```

*(Optional: If you ever rotate your key, simply run `echo -n "NEW_KEY" | gcloud secrets versions add gemini-api-key --data-file=-`. Cloud Run's `:latest` reference will automatically use the newest version on subsequent container starts).*

---

### Step 4: Create a Dedicated Cloud Run Service Account & Grant Access

In accordance with least-privilege security principles, create a dedicated service account and grant it permission to read the secret:

```bash
# 1. Create the dedicated service account
gcloud iam service-accounts create onboarding-assistant-sa \
  --display-name="Onboarding Assistant Cloud Run Service Account"

# 2. Grant Secret Accessor role on the specific secret
gcloud secrets add-iam-policy-binding gemini-api-key \
  --member="serviceAccount:onboarding-assistant-sa@${GCP_PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

### Step 5: Create Artifact Registry Repository & Build Container

```bash
# 1. Create Artifact Registry Docker repository (if it doesn't already exist)
gcloud artifacts repositories create ${ARTIFACT_REPO} \
  --repository-format=docker \
  --location=${GCP_REGION} \
  --description="Docker repository for Onboarding Assistant"

# 2. Build and push container image using Google Cloud Build
gcloud builds submit \
  --tag ${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${ARTIFACT_REPO}/${SERVICE_NAME}:latest .
```

---

### Step 6: Deploy to Google Cloud Run with Secret Injection

Deploy the service to Cloud Run. The `--set-secrets` parameter binds the Secret Manager secret directly to the container's `GEMINI_API_KEY` environment variable:

```bash
gcloud run deploy ${SERVICE_NAME} \
  --image ${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${ARTIFACT_REPO}/${SERVICE_NAME}:latest \
  --platform managed \
  --region ${GCP_REGION} \
  --service-account "onboarding-assistant-sa@${GCP_PROJECT_ID}.iam.gserviceaccount.com" \
  --port 3000 \
  --allow-unauthenticated \
  --set-env-vars ENVIRONMENT=production,ALLOWED_CORPORATE_DOMAIN=company.com \
  --set-secrets GEMINI_API_KEY=gemini-api-key:latest
```

---

### Step 7: Verify the Live Deployment

Retrieve the live Service URL and verify the health and chat endpoints:

```bash
# 1. Get the assigned HTTPS URL
export SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --platform managed --region ${GCP_REGION} --format 'value(status.url)')
echo "Service deployed at: ${SERVICE_URL}"

# 2. Test Health Endpoint
curl -i "${SERVICE_URL}/health"

# 3. Test Landing Screen with Day-1 Persona Bearer Token
curl -X POST "${SERVICE_URL}/api/v1/landing" \
  -H "Authorization: Bearer mock-google-token-rahul" \
  -H "Content-Type: application/json"

# 4. Open the Web Portal in your browser
echo "Open ${SERVICE_URL} in your browser to interact with the visual assistant."
```

---

## ❓ FAQ: Architecture & Framework Choice

### Why TypeScript & Express instead of Python & FastAPI?
- **AI Studio & Cloud Run Optimized**: AI Studio's browser runtime uses a Node.js sandbox that provides an instantaneous, interactive dev-server preview on port 3000 without requiring Python virtual environments, pip caching, or dual-process orchestration.
- **Single Cohesive Codebase**: The frontend UI (`public/index.html`) and backend API (`server.ts`) share common TypeScript interfaces (`src/types.ts`), eliminating schema duplication between client and server.
- **Fast Cold Starts on Cloud Run**: With `esbuild`, the entire application compiles into a single bundled JavaScript file (`dist/server.cjs`). When Cloud Run scales from zero instances, Node 22 starts in milliseconds compared to the module import overhead of heavy Python frameworks.
- **Simplicity & Zero Complex Dependencies**: The server does not require external ASGI server wrappers (such as Uvicorn or Gunicorn) or complex pip wheels. It starts cleanly with `node dist/server.cjs`.
- **First-Class Official Gemini SDK**: The official `@google/genai` TypeScript SDK provides clean, native typing for Gemini 2.5 Flash with minimal footprint.

