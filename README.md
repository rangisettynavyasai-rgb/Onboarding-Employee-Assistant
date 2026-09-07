# Patchamomma 2026: Secure AI-Powered Onboarding & Employee Assistant on GCP

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![Google Cloud Run](https://img.shields.io/badge/Google%20Cloud-Cloud%20Run-blue.svg)](https://cloud.google.com/run)
[![Tests Passing](https://img.shields.io/badge/tests-35%2F35%20passed-brightgreen.svg)]()

Production-grade **Multi-Agent AI Onboarding & Employee Assistant** in Python designed for deployment to **Google Cloud Run**, integrating with **Google Identity**, **Gemini**, **BigQuery Knowledge Mesh**, and **Google Cloud Storage (GCS)**.

---

## 🏛️ Security & System Architecture

```
                                [ Incoming Request ]
                                         │
                                         ▼
                           ┌───────────────────────────┐
                           │   Google Authentication   │ (Validates Google ID Token / IAP JWT)
                           └─────────────┬─────────────┘
                                         │ AuthenticatedPrincipal (sub, email, aud)
                                         ▼
                           ┌───────────────────────────┐
                           │ Employee Identity Mapping │ (sub -> trusted internal EmployeeRecord)
                           └─────────────┬─────────────┘
                                         │ EmployeeContext (EMP001, role, team, manager)
                                         ▼
                           ┌───────────────────────────┐
                           │   AuthorizationService    │ (Centralized RBAC/Policy Enforcement)
                           └─────────────┬─────────────┘
                                         │ Authorized Request Context
                                         ▼
                           ┌───────────────────────────┐
                           │     Session Security      │ (Validates session ownership by employee_id)
                           └─────────────┬─────────────┘
                                         │
                           ┌─────────────┴─────────────┐
                           ▼                           ▼
               ┌──────────────────────┐    ┌──────────────────────┐
               │ Multi-Agent System   │    │ Pre-Retrieval ACL    │
               │ (Orchestrator +      │    │ Knowledge Filtering  │
               │  Specialized Agents) │    │ (Team + Role checks) │
               └──────────┬───────────┘    └──────────┬───────────┘
                          │                           │
                          ▼                           ▼
               ┌──────────────────────┐    ┌──────────────────────┐
               │  Agent Tool Security │    │ Gemini 1.5 / 2.0 /   │
               │ (Context-Bound Tools │    │ Flash Generation     │
               │  No LLM User ID Arg) │    └──────────────────────┘
               └──────────────────────┘
```

---

## 🛡️ Core Security Boundaries

1. **Zero-Trust Token Identity**:
   - The frontend never submits `employee_id` in request payloads.
   - Authentication extracts `sub` from the Google ID token and resolves the trusted internal `EmployeeRecord`.
2. **Centralized RBAC Authorization**:
   - Centralized `AuthorizationService` governs all actions (`USE_ASSISTANT`, `VIEW_OWN_ONBOARDING`, `VIEW_TEAM_ONBOARDING`, `VIEW_DOCUMENT`, `MANAGE_PERMISSIONS`).
3. **Session Ownership Enforcement**:
   - Sessions are bound to `employee_id`. Attempting to access or hijack another employee's session ID returns `403 Forbidden`.
4. **Agent Tool Context Injection**:
   - Tools never take `employee_id` or `user_id` as LLM parameters.
   - Tools read the caller's identity directly from thread-safe Python `ContextVar`.
5. **Pre-Retrieval Knowledge ACLs**:
   - Documents in the Knowledge Mesh are tagged with `team` (`Payments`, `Platform`, `HR`, `IT`, `ALL`) and `access_level` (`employee`, `manager`, `hr`, `it`).
   - Unauthorized chunks are filtered at the repository query layer *before* entering Gemini's context window.

---

## 🤖 Multi-Agent Subsystem

| Agent | Responsibility | Key Tools |
| :--- | :--- | :--- |
| **Supervisor Agent** | Master Orchestrator: intent classification, session history, and sub-agent dispatch. | `dispatch(message, session, employee)` |
| **Onboarding Specialist Agent** | Welcomes Day-1 joiners, guides checklist tasks, explains next steps, and reports team progress. | `get_my_onboarding_status`, `complete_my_onboarding_task`, `get_team_onboarding_progress` |
| **Knowledge Detective Agent** | Grounded RAG across GCS manuals, blueprints, and video timestamp markers with pre-retrieval ACLs. | `search_company_knowledge` |
| **Code Mentor Agent** | Analyzes codebases, searches semantic index, and enforces corporate JSON structured logging guardrails. | `fetch_repository_context`, `apply_code_guardrails` |
| **Operations Action Agent** | Timesheet lookups, IT incident ticket dispatching, and 3-tier point-to-person lead escalations. | `check_my_timesheet_status`, `create_it_incident_ticket`, `resolve_team_blocker` |

---

## 👥 Representative Personas & Synthetic Datasets

| Employee ID | Name | Role | Authorization Role | Team | Key Scenario |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `EMP-2026-001` | Rahul Sharma | Software Engineer I | `employee` | Payments | Day-1 joiner, pending local dev setup |
| `EMP-2026-002` | Maya Lin | Cloud Infra Intern | `employee` | Platform | Day-1 intern, GKE cluster onboarding |
| `EMP-2026-003` | Liam Vance | Software Engineer II | `employee` | Payments | Existing engineer, overdue timesheet |
| `EMP-2026-004` | Carlos Santana | Senior Staff Data Engineer | `employee` | DataOps | Veteran staff engineer, fully onboarded |
| `EMP-2026-005` | Alex Chen | Platform Director | `manager` | Platform | Platform manager, lead escalation |
| `EMP-2026-006` | Priya Nair | Lead Backend Architect | `employee` | Payments | Tech lead & Rahul's onboarding buddy |
| `EMP-2026-008` | Marcus Vance | IT Systems Admin | `it` | IT | IT administrator, IAM key rotation |
| `EMP-2026-009` | Amanda Walker | Senior People Ops Specialist | `hr` | HR | HR specialist, compensation matrices |
| `EMP-2026-010` | Sarah Jenkins | Payments Engineering Manager | `manager` | Payments | Manager viewing team onboarding rollup |

---

## 🚀 Running Locally & Testing

### 1. Setup Virtual Environment
```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/macOS

pip install -r requirements.txt
```

### 2. Run Test Suite
```bash
pytest -v
```

### 3. Start Local FastAPI Development Server
```bash
uvicorn app.main:app --reload --port 8000
```

---

## ☁️ Google Cloud Run Deployment

### 1. Build and Push to Google Artifact Registry
```bash
gcloud builds submit --tag us-central1-docker.pkg.dev/YOUR_PROJECT_ID/patchamomma-repo/onboarding-agent:v1 .
```

### 2. Deploy to Cloud Run
```bash
gcloud run deploy patchamomma-onboarding-agent \
  --image us-central1-docker.pkg.dev/YOUR_PROJECT_ID/patchamomma-repo/onboarding-agent:v1 \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars ENVIRONMENT=production,AUTH_PROVIDER=google_oauth,REPOSITORY_BACKEND=bigquery,GCP_PROJECT_ID=YOUR_PROJECT_ID \
  --service-account onboarding-agent-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com
```
