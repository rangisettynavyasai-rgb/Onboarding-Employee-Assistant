# Enterprise AI Onboarding & Employee Assistant Framework

[![Node.js](https://img.shields.io/badge/Node.js-22_LTS-green.svg)](https://nodejs.org/)
[![Python](https://img.shields.io/badge/Python-3.10-yellow.svg)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-blue.svg)](https://www.typescriptlang.org/)
[![Google Cloud Run](https://img.shields.io/badge/Google%20Cloud-Cloud%20Run-blue.svg)](https://cloud.google.com/run)
[![Google Cloud Firestore](https://img.shields.io/badge/Database-Cloud%20Firestore-orange.svg)](https://cloud.google.com/firestore)
[![Gemini 3.6 Flash](https://img.shields.io/badge/Google%20GenAI-Gemini%203.6%20Flash-purple.svg)](https://ai.google.dev/)
[![Google Secret Manager](https://img.shields.io/badge/Security-Secret%20Manager-red.svg)](https://cloud.google.com/secret-manager)

Production-grade **Multi-Agent Enterprise Employee & Onboarding Assistant**. Engineered with a zero-trust **Node.js 22 Express Gateway** (`server.ts`), official **Google Gen AI SDK** (`@google/genai`), an enterprise **Python 3.10 Microservice** (`backend/`), and durable persistence powered by **Google Cloud Firestore**.

---

## 🏛️ System Architecture

```
                                [ Employee / Browser ]
                                           │
                                           ▼
                       ┌─────────────────────────────────────────┐
                       │   Google Identity Services (GIS) / SSO  │
                       │    "Continue with Google" Workspace     │
                       └────────────────────┬────────────────────┘
                                           │ Bearer Token / ID Token
                                           ▼
                       ┌─────────────────────────────────────────┐
                       │       Express Gateway (Node.js 22)      │
                       │               server.ts                 │
                       │  • Bearer Token / JWT Verification      │
                       │  • Server-Side Gemini 3.6 Flash Route   │
                       │  • Static UI & Web Client Hosting       │
                       └────────────────────┬────────────────────┘
                                           │ Zero-Copy JSON RPC
                                           ▼
                       ┌─────────────────────────────────────────┐
                       │    Python Microservice (Python 3.10)    │
                       │            backend/runner.py            │
                       │  • AuthService & Employee Resolution    │
                       │  • Supervisor Agent & Domain Mesh       │
                       │  • Dual-Mode Integration Engine         │
                       └───────┬─────────────────────────┬───────┘
                               │                         │
               ┌───────────────┘                         └───────────────┐
               ▼                                                         ▼
┌─────────────────────────────┐                           ┌─────────────────────────────┐
│    Cloud Firestore DB       │                           │  Enterprise Cloud Services  │
│  databaseId: ai-studio-...  │                           │  (Dual-Mode: Staging / Live)│
├─────────────────────────────┤                           ├─────────────────────────────┤
│ • /sessions/{sessionId}     │                           │ • Google Calendar API v3    │
│ • /employees/{employeeId}   │                           │   (OOO & Leave schedules)   │
│ • /tasks/{employeeId}       │                           │ • Atlassian Jira Cloud      │
│ • /timesheets/{timesheetId} │                           │   (ADF v3 Incidents)        │
│ • /incidents/{incidentId}   │                           │ • Salesforce CRM            │
└─────────────────────────────┘                           │   (TimeSheet sObjects)      │
                                                          └─────────────────────────────┘
```

---

## 📁 Project Structure & File Guide

| File / Path | Category | Purpose | Actively Used? |
| :--- | :--- | :--- | :--- |
| **`app.config.json`** | Configuration | **Single non-secret configuration file** for GitHub. Contains GCP project ID, Firestore DB name, Google OAuth Client ID, Jira host/project, Salesforce URL, and environment settings. | **Yes** — Loaded on startup by Node.js and Python. |
| **`.env.example`** | Configuration | Documentation template listing all environment variables and secrets. Never contains real secrets. | **Yes** — Deployment reference. |
| **`.gitignore`** | Security | Blocks secret files (`.env`), build outputs (`dist/`), `node_modules/`, and `__pycache__/` from Git. | **Yes** — Enforces security boundaries. |
| **`Dockerfile`** | Deployment | Multi-runtime container definition (Node.js 22 + Python 3) for Google Cloud Run. | **Yes** — Used for Cloud Run container builds. |
| **`package.json`** | Manifest | Defines dependencies (`express`, `@google/genai`, `cors`, `dotenv`, `esbuild`, `typescript`) and build scripts. | **Yes** — Build and dependency management. |
| **`tsconfig.json`** | Compiler | TypeScript compiler configuration for client and server code. | **Yes** — Typechecking and build validation. |
| **`metadata.json`** | Container | AI Studio runtime metadata (app name, capabilities, frame permissions). | **Yes** — Cloud container metadata. |
| **`server.ts`** | API Gateway | Express.js API gateway listening on port 3000. Handles routing, authentication, Gemini AI fallback, and bridges to Python. | **Yes** — Primary web application server. |
| **`src/pythonBridge.ts`** | IPC Bridge | Spawns Python 3 backend subprocess (`python3 -m backend.runner`), passes JSON via `stdin`, reads responses from `stdout`. | **Yes** — Connects Node.js to Python backend. |
| **`src/ui/app.ts`** | Frontend | Client-side TypeScript source. Handles Google Sign-In, onboarding checklist UI, timesheets, incident reporting, and chat. | **Yes** — Source for browser UI. |
| **`public/index.html`** | Frontend | Single-page application entry point HTML. Injects Google Identity Services SDK and layout components. | **Yes** — Served by Express to browser. |
| **`public/app.js`** | Frontend | Compiled client-side JavaScript bundle generated from `src/ui/app.ts` via esbuild. | **Yes** — Executed in user's browser. |
| **`backend/runner.py`** | Python Microservice | Entry point for Python IPC calls. Parses incoming action payloads and routes to the appropriate domain service. | **Yes** — Main execution router. |
| **`backend/config.py`** | Python Microservice | Configuration loader. Resolves variables in priority order: environment variables / Secret Manager first, `app.config.json` second. | **Yes** — Used across Python modules. |
| **`backend/firestore.py`** | Database | `FirestoreManager` handling persistent read/write calls to Google Cloud Firestore with safe in-memory fallback. | **Yes** — Cloud Firestore persistence layer. |
| **`backend/models.py`** | Data Models | Dataclasses and TypedDicts for Employees, Tasks, Timesheets, Incidents, and Chat Messages. | **Yes** — Type definitions. |
| **`backend/data.py`** | Knowledge Mesh | Embedded enterprise knowledge documents (Security policies, dev setup, benefits) and employee seed directory. | **Yes** — RAG context and employee lookups. |
| **`backend/auth_policy.py`** | Security | Role-Based Access Control (RBAC) engine verifying permissions for employees, managers, HR, and IT. | **Yes** — Authorization and policy enforcement. |
| **`backend/services.py`** | Service Layer | Business logic implementation (`AuthService`, `OnboardingService`, `TimesheetService`, `KnowledgeService`, `IncidentService`). | **Yes** — Core application services. |
| **`backend/agents.py`** | AI Agents | Multi-agent reasoning pipeline (`TriageAgent`, `PolicyLookupAgent`, `ActionRouterAgent`, `SecurityAuditAgent`). | **Yes** — Conversational AI pipeline. |
| **`backend/state_store.py`** | State | Coordinates session state and synchronizes memory caches with Cloud Firestore. | **Yes** — State management. |
| **`backend/jira_service.py`** | Integration | Atlassian Jira Cloud REST API integration with automatic Firestore staging fallback. | **Yes** — Incident ticket sync. |
| **`backend/salesforce_service.py`** | Integration | Salesforce REST API integration with automatic Firestore staging fallback. | **Yes** — Timesheet sync. |
| **`backend/calendar_service.py`** | Integration | Team availability tracker and Out-Of-Office (OOO) calendar resolver. | **Yes** — Team availability display. |
| **`bigquery/tables.sql`** | Analytics | DDL schema scripts for enterprise analytics tables in Google BigQuery. | **Reference only** — Analytical schema documentation; not executed at runtime. |
| **`bigquery/seed_data.sql`** | Analytics | Sample INSERT statements for BigQuery analytics reporting. | **Reference only** — Analytical sample data; not executed at runtime. |

---

## ⚙️ Configuration & Variable Directory

The application cleanly separates **Non-Secret Configuration** (committed in `app.config.json`) from **Sensitive Secrets** (stored in Google Secret Manager / local `.env`).

```
┌────────────────────────────────────────────────────────┐
│                   app.config.json                      │
│     (Safe for GitHub - Non-Secret Settings)            │
│  • environment          • jira.host                    │
│  • gcpProjectId         • jira.projectKey              │
│  • firestoreDatabaseId  • salesforce.instanceUrl       │
│  • googleOAuthClientId  • allowedCorporateDomain       │
└──────────────────────────┬─────────────────────────────┘
                           │ Baseline defaults
                           ▼
┌────────────────────────────────────────────────────────┐
│             Google Secret Manager / os.environ         │
│     (NEVER committed to GitHub - Sensitive Secrets)    │
│  • GEMINI_API_KEY       • JIRA_API_TOKEN               │
│  • JIRA_EMAIL           • SALESFORCE_ACCESS_TOKEN      │
└──────────────────────────┬─────────────────────────────┘
                           │ Injected at Cloud Run runtime
                           ▼
              [ Running Container Application ]
```

### 1. Non-Secret Variables (`app.config.json`)

These variables contain no credentials or private keys and are safe to version control:

| Key in `app.config.json` | Environment Variable Equivalent | Where to Get This Value | Current Value / Example |
| :--- | :--- | :--- | :--- |
| `environment` | `ENVIRONMENT` | Choose deployment stage: `development`, `staging`, or `production`. | `"development"` |
| `allowedCorporateDomain` | `ALLOWED_CORPORATE_DOMAIN` | Your Google Workspace corporate domain (e.g. `yourcompany.com`) or `*` to allow all domains. | `"*"` |
| `gcpProjectId` | `GCP_PROJECT_ID` | **Google Cloud Console** ➔ Top project dropdown ➔ Copy the **Project ID** (e.g. `gen-lang-client-0448180018` or `my-prod-project`). Or run: `gcloud config get-value project`. | `"gen-lang-client-0448180018"` |
| `firestoreDatabaseId` | `FIRESTORE_DATABASE_ID` | **GCP Console** ➔ **Firestore** ➔ **Databases**. Use `(default)` if you created a standard database, or the custom database ID if multiple databases exist. | `"ai-studio-onboardingemploy-b1158660-8824-4e90-b842-3a0f086d1796"` |
| `googleOAuthClientId` | `GOOGLE_OAUTH_CLIENT_ID` | **GCP Console** ➔ **APIs & Services** ➔ **Credentials** ➔ Under **OAuth 2.0 Client IDs**, select your Web Application client (ends with `.apps.googleusercontent.com`). | `"267990013452-k48vsk24b87fcb8pk0c0mlrs47pjqgvf.apps.googleusercontent.com"` |
| `jira.host` | `JIRA_HOST` | Your Atlassian Jira site URL (e.g. `https://yourcompany.atlassian.net`). | `"https://jira.company.internal"` |
| `jira.projectKey` | `JIRA_PROJECT_KEY` | **Atlassian Jira** ➔ **Projects** ➔ Project abbreviation key (e.g. `OPS`, `IT`, `HELP`). | `"OPS"` |
| `salesforce.instanceUrl` | `SALESFORCE_INSTANCE_URL` | **Salesforce Setup** ➔ **Company Settings** ➔ **My Domain** ➔ URL (e.g. `https://yourcompany.my.salesforce.com`). | `"https://salesforce.company.internal"` |

---

### 2. Sensitive Secrets (Google Secret Manager / Local `.env`)

These credentials must **NEVER** be committed to Git. Store them in Google Cloud Secret Manager for Cloud Run deployments, or in a local uncommitted `.env` file for local development:

| Secret Name | Purpose | Where to Obtain Value | How to Create in GCP Secret Manager |
| :--- | :--- | :--- | :--- |
| **`GEMINI_API_KEY`** | Powers server-side Gemini 3.6 Flash conversational intelligence. | **Google AI Studio** (https://aistudio.google.com/app/apikey) ➔ Click **"Create API key"**. Or GCP Console Vertex AI credentials. | `echo -n "AIzaSy..." \| gcloud secrets create gemini-api-key --data-file=-` |
| **`JIRA_EMAIL`** | Account email for Atlassian Jira REST API authentication. | The email address associated with your Atlassian Cloud account. | `echo -n "admin@company.com" \| gcloud secrets create jira-email --data-file=-` |
| **`JIRA_API_TOKEN`** | API token for Jira ticket creation. | **Atlassian Account Settings** ➔ **Security** ➔ **API tokens** (https://id.atlassian.com/manage-profile/security/api-tokens) ➔ Click **"Create API token"**. | `echo -n "ATATT3x..." \| gcloud secrets create jira-api-token --data-file=-` |
| **`SALESFORCE_ACCESS_TOKEN`** | OAuth / Personal Token for Salesforce timesheet synchronization. | **Salesforce Settings** ➔ **Reset My Security Token** (combined with password) or Connected App OAuth Bearer token. | `echo -n "00D8X..." \| gcloud secrets create salesforce-token --data-file=-` |

> **Note on Dual-Mode Fallback:** If Jira or Salesforce secrets are omitted, the application will not crash. It will automatically run in **Firestore Staging Mode**, saving valid Jira ADF documents and Salesforce sObjects in Cloud Firestore for later batch synchronization.

---

## 🚀 Step-by-Step Cloud Run Deployment

### 1. Configure GCP Project & APIs

```bash
export GCP_PROJECT_ID="gen-lang-client-0448180018"
export GCP_REGION="us-central1"
export SERVICE_NAME="onboarding-assistant"
export ARTIFACT_REPO="enterprise-apps"

gcloud config set project ${GCP_PROJECT_ID}

# Enable required Google Cloud APIs
gcloud services enable \
  run.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  firestore.googleapis.com
```

### 2. Store Secrets in Google Secret Manager

```bash
# 1. Gemini API Key (Required for AI chat)
echo -n "YOUR_GEMINI_API_KEY" | gcloud secrets create gemini-api-key \
  --replication-policy="automatic" \
  --data-file=-

# 2. (Optional) Jira Credentials for Live Sync
echo -n "YOUR_JIRA_EMAIL" | gcloud secrets create jira-email \
  --replication-policy="automatic" \
  --data-file=-

echo -n "YOUR_JIRA_API_TOKEN" | gcloud secrets create jira-api-token \
  --replication-policy="automatic" \
  --data-file=-

# 3. (Optional) Salesforce Credentials for Live Sync
echo -n "YOUR_SALESFORCE_ACCESS_TOKEN" | gcloud secrets create salesforce-token \
  --replication-policy="automatic" \
  --data-file=-
```

### 3. Configure Service Account Permissions

```bash
# Create dedicated Cloud Run Service Account
gcloud iam service-accounts create onboarding-assistant-sa \
  --display-name="Onboarding Assistant Runtime SA"

# Grant Secret Manager Secret Accessor role
gcloud projects add-iam-policy-binding ${GCP_PROJECT_ID} \
  --member="serviceAccount:onboarding-assistant-sa@${GCP_PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Grant Cloud Datastore User role (for Cloud Firestore access)
gcloud projects add-iam-policy-binding ${GCP_PROJECT_ID} \
  --member="serviceAccount:onboarding-assistant-sa@${GCP_PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/datastore.user"
```

### 4. Build and Deploy to Cloud Run

```bash
# 1. Create Artifact Registry Docker repository (one-time setup)
gcloud artifacts repositories create ${ARTIFACT_REPO} \
  --repository-format=docker \
  --location=${GCP_REGION}

# 2. Build container image using Cloud Build
gcloud builds submit \
  --tag ${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${ARTIFACT_REPO}/${SERVICE_NAME}:latest .

# 3. Deploy to Cloud Run with Secret Manager binding
gcloud run deploy ${SERVICE_NAME} \
  --image ${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${ARTIFACT_REPO}/${SERVICE_NAME}:latest \
  --platform managed \
  --region ${GCP_REGION} \
  --service-account "onboarding-assistant-sa@${GCP_PROJECT_ID}.iam.gserviceaccount.com" \
  --port 3000 \
  --allow-unauthenticated \
  --set-secrets="GEMINI_API_KEY=gemini-api-key:latest,JIRA_API_TOKEN=jira-api-token:latest,SALESFORCE_ACCESS_TOKEN=salesforce-token:latest"
```

---

## 🛠️ Local Development

```bash
# 1. Install dependencies
npm install

# 2. (Optional) Set up local secrets in .env for development
cp .env.example .env
# Edit .env with your local GEMINI_API_KEY

# 3. Compile frontend bundle
npm run build:ui

# 4. Start local development server
npm run dev
```

Visit `http://localhost:3000` to access the application.
