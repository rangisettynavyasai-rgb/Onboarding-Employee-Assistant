"""
FastAPI Cloud Run Application for Patchamomma 2026.
Secure AI-Powered Onboarding & Employee Assistant Framework.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, Request, Depends, HTTPException, Query, status, Response
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.exceptions import AppException
from app.core.logging import logger, log_audit_event
from app.models import (
    EmployeeRecord,
    ChatRequest,
    ChatResponse,
    LandingResponse,
    TaskCompletionRequest,
    IncidentCreateRequest,
    IncidentRecord,
    OnboardingChecklist,
    TeamOnboardingSummary,
)
from app.dependencies import (
    get_current_employee,
    get_authenticated_session,
    session_service,
    onboarding_service,
    knowledge_service,
    timesheet_service,
    incident_service,
    proactive_service,
    UserSession,
)
from app.agents.supervisor_agent import supervisor_agent

# Initialize FastAPI Application
app = FastAPI(
    title="Patchamomma 2026 Secure Multi-Agent Assistant",
    description="Enterprise AI Onboarding & Employee Assistant grounded in GCP, BigQuery, GCS, Firestore, and Google Identity.",
    version="2026.1.0",
)

# Enable CORS for internal corporate portals
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

@app.exception_handler(AppException)
async def handle_app_exception(request: Request, exc: AppException):
    """Centralized handler mapping domain exceptions to clean HTTP responses."""
    logger.warning(f"HTTP {exc.status_code} Error on {request.url.path}: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "message": exc.message,
            "details": exc.details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


# ============================================================================
# 1. CLOUD RUN HEALTH PROBE
# ============================================================================

@app.get("/health", tags=["System"])
def health_check():
    """Liveness & Readiness probe for Google Cloud Run container serving."""
    return {
        "status": "HEALTHY",
        "service": "patchamomma-onboarding-agent",
        "environment": settings.ENVIRONMENT,
        "auth_provider": settings.AUTH_PROVIDER,
        "allowed_corporate_domain": settings.ALLOWED_CORPORATE_DOMAIN,
        "session_store_backend": settings.SESSION_STORE_BACKEND,
        "repository_backend": settings.REPOSITORY_BACKEND,
        "model": settings.GEMINI_MODEL,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================================
# 2. PROACTIVE LANDING ENDPOINT
# ============================================================================

@app.post("/api/v1/landing", response_model=LandingResponse, tags=["Onboarding"])
def proactive_landing(current_employee: EmployeeRecord = Depends(get_current_employee)):
    """
    Proactive Guided Landing:
    Automatically evaluates Day-1 status and pending onboarding milestones without requiring
    the employee to formulate a prompt.
    """
    landing_data = proactive_service.generate_proactive_landing(current_employee)
    return LandingResponse(
        employee_id=current_employee.employee_id,
        name=current_employee.name,
        is_day_one=current_employee.is_day_one,
        proactive_greeting=landing_data["proactive_greeting"],
        onboarding_summary=landing_data["onboarding_summary"],
    )


# ============================================================================
# 3. INTERACTIVE MULTI-AGENT CHAT ENDPOINT
# ============================================================================

@app.post("/api/v1/chat", response_model=ChatResponse, tags=["Assistant"])
def interactive_chat(
    req: ChatRequest,
    current_employee: EmployeeRecord = Depends(get_current_employee),
    session: UserSession = Depends(get_authenticated_session),
):
    """
    Core interactive chat route coordinating multi-agent orchestration.
    Identity is extracted from verified Google token (Zero-Trust).
    Session ownership is verified to prevent cross-account conversation hijacking.
    """
    response_text, agent_name = supervisor_agent.dispatch(
        user_message=req.message,
        session=session,
        employee=current_employee,
    )

    # Persist updated session history to Firestore / Memory
    session_service.persist_session(session)

    suggested_actions = []
    if "timesheet" in req.message.lower():
        suggested_actions = ["Submit Timesheet Portal", "Check Team Timesheets"]
    elif "onboard" in req.message.lower() or current_employee.is_day_one:
        suggested_actions = ["Complete Next Task", "View Onboarding Checklist", "Search Runbooks"]

    return ChatResponse(
        response=response_text,
        session_id=session.session_id,
        agent_invoked=agent_name,
        suggested_actions=suggested_actions,
    )


# ============================================================================
# 4. CONVERSE GATEWAY (PHASE C & E PAY-PER-TOKEN AI GATEWAY)
# ============================================================================

@app.post("/api/v1/assistant/converse", tags=["Conversational Layer"])
def execute_chat_interaction(
    session_id: Optional[str] = Query(None),
    user_prompt: str = Query(..., min_length=1),
    current_employee: EmployeeRecord = Depends(get_current_employee),
    session: UserSession = Depends(get_authenticated_session),
):
    """
    Direct pay-per-token conversational processing gateway:
    1. Authenticates caller and verifies corporate domain perimeter.
    2. Enforces anti-hijacking by binding session to verified employee_id.
    3. Stamps security perimeter (department/team/clearance) into retrieval context.
    4. Executes pay-per-token model generation without persistent compute fees.
    5. Records turns in session history.
    """
    session.append_message("user", user_prompt)

    # Pre-Retrieval RAG: Query authorized knowledge and stamp security perimeter
    chunks = knowledge_service.search_authorized_knowledge(current_employee, user_prompt)
    context_data = knowledge_service.format_chunks_for_context(current_employee, chunks, user_prompt)

    # Generate response securely
    ai_response = supervisor_agent.generate_direct_response(user_prompt, context_data)

    session.append_message("assistant", ai_response)
    session_service.persist_session(session)

    return {
        "session_id": session.session_id,
        "employee_id": current_employee.employee_id,
        "department": current_employee.department,
        "history_depth": len(session.history),
        "response": ai_response,
    }


# ============================================================================
# 5. DIRECT ONBOARDING REST API
# ============================================================================

@app.get("/api/v1/onboarding/my-status", response_model=OnboardingChecklist, tags=["Onboarding"])
def get_my_onboarding(current_employee: EmployeeRecord = Depends(get_current_employee)):
    """Retrieves the authenticated employee's active onboarding checklist."""
    return onboarding_service.get_employee_checklist(current_employee, current_employee.employee_id)


@app.post("/api/v1/onboarding/complete-task", response_model=OnboardingChecklist, tags=["Onboarding"])
def complete_task(
    req: TaskCompletionRequest,
    current_employee: EmployeeRecord = Depends(get_current_employee),
):
    """Marks an onboarding task as completed for the authenticated employee."""
    return onboarding_service.complete_onboarding_task(current_employee, req.task_id)


@app.get("/api/v1/onboarding/team-progress", response_model=TeamOnboardingSummary, tags=["Onboarding"])
def get_team_progress(
    team: Optional[str] = Query(None),
    current_employee: EmployeeRecord = Depends(get_current_employee),
):
    """
    Manager endpoint: Returns onboarding progress rollup for caller's team.
    Enforces MANAGER or HR role clearance.
    """
    return onboarding_service.get_team_onboarding_progress(current_employee, team)


# ============================================================================
# 6. KNOWLEDGE & OPERATIONS REST API
# ============================================================================

@app.get("/api/v1/knowledge/search", tags=["Knowledge Mesh"])
def search_knowledge(
    query: str = Query(..., min_length=2),
    current_employee: EmployeeRecord = Depends(get_current_employee),
):
    """Searches knowledge mesh with pre-retrieval ACL enforcement."""
    chunks = knowledge_service.search_authorized_knowledge(current_employee, query)
    return {
        "query": query,
        "results_count": len(chunks),
        "results": [c.model_dump() for c in chunks],
    }


@app.get("/api/v1/timesheets/my-status", tags=["Operations"])
def check_timesheet(current_employee: EmployeeRecord = Depends(get_current_employee)):
    """Checks the authenticated employee's timesheet status."""
    return timesheet_service.get_timesheet_status(current_employee, current_employee.employee_id)


@app.post("/api/v1/incidents/create", response_model=IncidentRecord, tags=["Operations"])
def create_incident(
    req: IncidentCreateRequest,
    current_employee: EmployeeRecord = Depends(get_current_employee),
):
    """Creates a new IT or Platform incident ticket."""
    return incident_service.create_incident(
        actor=current_employee,
        category=req.category,
        summary=req.summary,
        severity=req.severity,
        confirmed=req.confirmed,
    )


# ============================================================================
# 7. STATIC CLIENT PORTAL SERVING
# ============================================================================

@app.get("/", response_class=HTMLResponse, tags=["Portal"])
def serve_portal():
    """Serves the frontend enterprise employee onboarding portal."""
    static_file = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if not settings.GOOGLE_OAUTH_CLIENT_ID:
        raise HTTPException(status_code=503, detail="GOOGLE_OAUTH_CLIENT_ID not configured.")

    if os.path.exists(static_file):
        with open(static_file, "r", encoding="utf-8") as f:
            html_content = f.read()
            html_content = html_content.replace("__GOOGLE_CLIENT_ID__", settings.GOOGLE_OAUTH_CLIENT_ID)
            html_content = html_content.replace("GOOGLE_CLIENT_ID_PLACEHOLDER", settings.GOOGLE_OAUTH_CLIENT_ID)
            return HTMLResponse(content=html_content)

    return HTMLResponse("<html><body><h1>Patchamomma AI Onboarding Assistant</h1></body></html>")
