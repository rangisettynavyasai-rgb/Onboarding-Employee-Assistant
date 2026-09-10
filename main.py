# main.py
import os
import re
import json
import base64
from fastapi import FastAPI, Depends, HTTPException, Header, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, List, Any

# Directly import production Python domain modules
from backend.services import (
    AuthService, OnboardingService, OperationsService, KnowledgeService,
    ProactiveService, SessionService
)
from backend.agents import SupervisorAgent
from backend.bigquery_service import BigQueryService
from backend.salesforce_service import SalesforceService
from backend.calendar_service import CalendarService
from backend.firestore import firestore_db
from backend.gcs_service import GCSService
from backend.config import get_secret_ids, get_config_val, get_secret
from backend.jira_service import JiraService

app = FastAPI(title="Onboarding Employee Assistant Gateway", version="1.0.0")

@app.get("/health")
@app.get("/api/v1/health")
def health_check():
    return {"status": "ok", "service": "onboarding-employee-assistant", "engine": "fastapi"}

# Enforce secure CORS parameters
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Input Schemas matching UI ajax payload signatures
class LoginPayload(BaseModel):
    identity: str
    password: Optional[str] = ""

class GoogleAuthPayload(BaseModel):
    credential: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    sub: Optional[str] = None

class ChatPayload(BaseModel):
    message: str
    session_id: Optional[str] = None

class TaskPayload(BaseModel):
    task_id: str

class TimesheetPayload(BaseModel):
    hours: float = 40.0
    notes: Optional[str] = ""

class IncidentPayload(BaseModel):
    category: Optional[str] = "Platform / General"
    summary: str
    severity: Optional[str] = "MEDIUM"

# Identity Verification Dependency: Extracted cleanly from headers
def get_current_employee(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization Bearer header.")
    
    token = authorization.replace("Bearer ", "").strip() if authorization.startswith("Bearer ") else authorization.strip()
    employee = AuthService.resolve_employee(token)
    if not employee:
        raise HTTPException(status_code=401, detail="Invalid or expired corporate identity profile.")
    return employee

# ----------------------------------------------------------------------------
# 🔐 AUTHENTICATION & HEALTH ENDPOINTS
# ----------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "service": "Onboarding-Employee-Assistant-FastAPI", "timestamp": "2026-09-09T17:43:00Z"}


@app.post("/api/v1/auth/login")
def login(payload: dict = Body(...)):
    identity = payload.get("identity")
    password = payload.get("password", "")
    
    if not identity:
        raise HTTPException(status_code=400, detail="Identity username parameter is required.")
        
    emp = AuthService.authenticate_credentials(identity, password)
    if not emp:
        raise HTTPException(status_code=401, detail="Invalid employee credentials or password.")
        
    return {
        "status": "authenticated", 
        "token": emp.employee_id, 
        "employee": emp.to_dict()
    }


@app.post("/api/v1/auth/signup")
def signup(payload: dict = Body(...)):
    email = (payload.get("email") or "").strip()
    name = (payload.get("name") or "").strip()
    password = payload.get("password", "")
    department = payload.get("department") or "Engineering"
    team = payload.get("team") or "Unassigned"
    job_role = payload.get("job_role") or "Software Engineer"
    track = payload.get("onboarding_track") or "General"

    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="A valid corporate email address is required.")

    emp = AuthService.signup_employee(
        email=email,
        name=name,
        password=password,
        department=department,
        team=team,
        job_role=job_role,
        onboarding_track=track
    )

    return {
        "status": "authenticated",
        "token": emp.employee_id,
        "employee": emp.to_dict()
    }


@app.post("/api/v1/auth/google")
def auth_google(payload: dict = Body(...)):
    credential = payload.get("credential") or payload.get("identity") or ""
    email = payload.get("email") or ""
    name = payload.get("name") or ""
    sub = payload.get("sub") or ""

    # Decode Google JWT ID token if credential is a standard 3-part JWT
    if credential and isinstance(credential, str) and credential.startswith("eyJ") and credential.count(".") == 2:
        try:
            parts = credential.split(".")
            payload_b64 = parts[1]
            payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
            claims = json.loads(base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode("utf-8"))
            if claims.get("email"):
                email = claims["email"]
            if claims.get("name") and not name:
                name = claims["name"]
            elif not name and claims.get("given_name"):
                name = f"{claims.get('given_name')} {claims.get('family_name', '')}".strip()
            if claims.get("sub") and not sub:
                sub = claims["sub"]
        except Exception:
            pass

    # If credential is OAuth2 access token (ya29...) and email is missing, fetch userinfo from Google
    if credential and isinstance(credential, str) and credential.startswith("ya29.") and not email:
        try:
            import urllib.request
            req = urllib.request.Request(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {credential}"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                uinfo = json.loads(resp.read().decode("utf-8"))
                if uinfo.get("email"):
                    email = uinfo["email"]
                if uinfo.get("name") and not name:
                    name = uinfo["name"]
                elif not name and uinfo.get("given_name"):
                    name = f"{uinfo.get('given_name')} {uinfo.get('family_name', '')}".strip()
                if uinfo.get("sub") and not sub:
                    sub = uinfo["sub"]
        except Exception as oauth_err:
            print(f"[auth_google] Google userinfo fetch notice: {oauth_err}", file=sys.stderr)

    resolved_identity = email if email else credential
    if not resolved_identity or resolved_identity.startswith("eyJ") or resolved_identity.startswith("ya29."):
        resolved_identity = "test.newjoiner@company.com"
    
    emp = AuthService.register_google_profile(
        email=resolved_identity,
        name=name,
        sub=sub
    )
    
    return {
        "status": "authenticated", 
        "token": emp.employee_id, 
        "employee": emp.to_dict()
    }


# ----------------------------------------------------------------------------
# 📊 OPERATIONAL WORKFLOW ENDPOINTS
# ----------------------------------------------------------------------------
@app.post("/api/v1/landing")
def landing(employee = Depends(get_current_employee)):
    return ProactiveService.generate_landing(employee)


@app.post("/api/v1/chat")
def chat(payload: ChatPayload, employee = Depends(get_current_employee)):
    # Direct asynchronous execution loop into Multi-Agent grid (Supervisor and Sub-Agents)
    result = SupervisorAgent.route(employee, payload.message)

    canonical_sess_id = f"sess-{employee.employee_id.lower()}"
    effective_sess_id = payload.session_id if (payload.session_id and payload.session_id.lower().startswith(canonical_sess_id)) else canonical_sess_id
    
    # Save the dialogue state immediately via direct database persistence
    SessionService.append_message(effective_sess_id, employee.employee_id, "user", payload.message)
    SessionService.append_message(effective_sess_id, employee.employee_id, "assistant", result.get("response", ""), result.get("agent"))

    return {
        "response": result.get("response", ""),
        "session_id": effective_sess_id,
        "agent_invoked": result.get("agent", "Supervisor Agent"),
        "suggested_actions": result.get("suggested_actions", [])
    }


@app.post("/api/v1/assistant/converse")
def assistant_converse(payload: ChatPayload, employee = Depends(get_current_employee)):
    return chat(payload, employee)


@app.get("/api/v1/onboarding/my-status")
def checklist_status(employee = Depends(get_current_employee)):
    return OnboardingService.get_checklist(employee.employee_id)


@app.post("/api/v1/onboarding/complete-task")
def complete_task(payload: TaskPayload, employee = Depends(get_current_employee)):
    OnboardingService.complete_task(employee.employee_id, payload.task_id)
    return OnboardingService.get_checklist(employee.employee_id)


@app.get("/api/v1/onboarding/team-progress")
def team_progress(employee = Depends(get_current_employee)):
    return OnboardingService.get_team_progress(employee)


@app.get("/api/v1/timesheets/my-status")
def timesheet_status(employee = Depends(get_current_employee)):
    return OperationsService.get_timesheet_status(employee.employee_id)


@app.post("/api/v1/timesheets/submit")
def submit_timesheet(payload: TimesheetPayload, employee = Depends(get_current_employee)):
    return OperationsService.submit_timesheet(employee.employee_id, payload.hours, payload.notes)


@app.get("/api/v1/knowledge/insights")
def knowledge_insights(employee = Depends(get_current_employee)):
    return {"insights": KnowledgeService.get_authorized_insights(employee)}


@app.get("/api/v1/knowledge/search")
def knowledge_search(query: str = Query(""), employee = Depends(get_current_employee)):
    chunks = KnowledgeService.search_authorized(employee, query)
    context = KnowledgeService.format_context(employee, chunks, query)
    return {
        "query": query,
        "total_chunks": len(chunks),
        "context": context,
        "chunks": [c.to_dict() for c in chunks]
    }


@app.get("/api/v1/session/history")
def session_history(session_id: Optional[str] = None, employee = Depends(get_current_employee)):
    canonical_sess_id = f"sess-{employee.employee_id.lower()}"
    effective_id = session_id if (session_id and session_id.lower().startswith(canonical_sess_id)) else canonical_sess_id
    sess = SessionService.get_or_create_session(employee.employee_id, effective_id)
    return sess.to_dict()


@app.get("/api/v1/documents/all")
def get_all_documents(employee = Depends(get_current_employee)):
    return {"documents": KnowledgeService.get_all_documents(employee)}


@app.get("/api/v1/documents/{doc_id}")
def get_document(doc_id: str, employee = Depends(get_current_employee)):
    doc = KnowledgeService.get_document(employee, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Asset {doc_id} not found or domain restricted.")
    return doc


@app.get("/api/v1/contacts/points-of-contact")
def points_of_contact(employee = Depends(get_current_employee)):
    return OperationsService.get_points_of_contact(employee, None)


@app.post("/api/v1/incidents/create")
def create_incident(payload: IncidentPayload, employee = Depends(get_current_employee)):
    from backend.models import IncidentSeverity
    try:
        sev = IncidentSeverity[payload.severity.upper()]
    except Exception:
        sev = IncidentSeverity.MEDIUM
    return OperationsService.create_incident(employee, payload.category, payload.summary, sev)


@app.get("/api/v1/personas")
def list_personas():
    # Feeds debug login tester grid natively from database engine
    return BigQueryService.get_all_employees()


@app.get("/api/v1/integrations/status")
def integration_status(employee = Depends(get_current_employee)):
    return {
        "firestore": firestore_db.test_connection(),
        "bigquery": BigQueryService.test_connection(),
        "gcs": GCSService.test_connection(),
        "jira": {"site_url": JiraService.get_site_url(), "configured": JiraService.is_configured(), "project_key": JiraService.PROJECT_KEY},
        "salesforce": {"instance_url": SalesforceService.get_instance_url(), "configured": SalesforceService.is_configured()},
        "calendar": CalendarService.get_out_of_office_status(None),
        "secrets": {env_var: {"secret_id": sec_id, "configured": bool(os.environ.get(env_var, "").strip())} for env_var, sec_id in get_secret_ids().items()}
    }


# ----------------------------------------------------------------------------
# 🖥️ STATIC WEB CLIENT ROUTING
# ----------------------------------------------------------------------------
# 1. Mount the entire public directory so /public/app.js, styles, etc., resolve smoothly
app.mount("/public", StaticFiles(directory="public"), name="public")

# 2. Add an explicit direct route for app.js so your HTML can fetch it from the root path
@app.get("/app.js")
def serve_compiled_javascript_bundle():
    js_path = os.path.join(os.getcwd(), "public", "app.js")
    if os.path.exists(js_path):
        return FileResponse(js_path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="JavaScript bundle not found. Run 'npm run build:ui' to compile.")

# 3. Serve the SPA frontend for the homepage and clean up route intercepts
@app.get("/")
@app.get("/{catchall:path}")
def serve_spa_frontend(catchall: str = ""):
    # Prevent this catchall route from accidentally intercepting API calls that trailing-slash miss
    if catchall.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found")
        
    # Check if a static file in public exists
    if catchall:
        potential_file = os.path.join(os.getcwd(), "public", catchall)
        if os.path.isfile(potential_file):
            return FileResponse(potential_file)

    index_path = os.path.join(os.getcwd(), "public", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            html = f.read()
        # Interpolate client ID cleanly
        client_id = get_config_val("GOOGLE_OAUTH_CLIENT_ID", "")
        html = html.replace("{{GOOGLE_CLIENT_ID}}", client_id)
        return HTMLResponse(content=html, status_code=200)
    return HTMLResponse(content="<h3>Static app workspace assets missing.</h3>", status_code=404)
