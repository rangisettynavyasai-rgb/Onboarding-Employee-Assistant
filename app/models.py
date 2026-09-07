"""
Domain Models and API Schemas for Patchamomma 2026.
Uses Pydantic v2 for data validation, serialization, and typing.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, EmailStr


# ============================================================================
# ENUMS
# ============================================================================

class AuthorizationRole(str, Enum):
    EMPLOYEE = "employee"
    MANAGER = "manager"
    HR = "hr"
    IT = "it"


class AccessLevel(str, Enum):
    EMPLOYEE = "employee"
    MANAGER = "manager"
    HR = "hr"
    IT = "it"


class TeamDomain(str, Enum):
    PAYMENTS = "Payments"
    PLATFORM = "Platform"
    DATA_OPS = "DataOps"
    HR = "HR"
    IT = "IT"
    ALL = "ALL"


class OnboardingStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"


class TimesheetStatus(str, Enum):
    SUBMITTED = "SUBMITTED"
    PENDING = "PENDING"
    OVERDUE = "OVERDUE"
    APPROVED = "APPROVED"


class IncidentSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AuthAction(str, Enum):
    USE_ASSISTANT = "USE_ASSISTANT"
    VIEW_OWN_PROFILE = "VIEW_OWN_PROFILE"
    VIEW_OWN_ONBOARDING = "VIEW_OWN_ONBOARDING"
    COMPLETE_OWN_ONBOARDING_TASK = "COMPLETE_OWN_ONBOARDING_TASK"
    VIEW_TEAM_MEMBERS = "VIEW_TEAM_MEMBERS"
    VIEW_TEAM_ONBOARDING = "VIEW_TEAM_ONBOARDING"
    VIEW_EMPLOYEE_PROFILE = "VIEW_EMPLOYEE_PROFILE"
    VIEW_EMPLOYEE_ONBOARDING = "VIEW_EMPLOYEE_ONBOARDING"
    UPDATE_EMPLOYEE_ONBOARDING = "UPDATE_EMPLOYEE_ONBOARDING"
    MANAGE_PERMISSIONS = "MANAGE_PERMISSIONS"
    VIEW_DOCUMENT = "VIEW_DOCUMENT"
    CHECK_TIMESHEET = "CHECK_TIMESHEET"
    CREATE_INCIDENT = "CREATE_INCIDENT"


# ============================================================================
# IDENTITY & EMPLOYEE MODELS
# ============================================================================

class AuthenticatedPrincipal(BaseModel):
    """Represents a verified external Google identity."""
    subject: str = Field(..., description="Google unique subject ID (sub)")
    email: EmailStr = Field(..., description="User Google email address")
    name: Optional[str] = Field(default=None, description="Display name from Google token")
    issuer: str = Field(default="accounts.google.com", description="Token issuer")
    audience: Optional[str] = Field(default=None, description="Client ID audience")
    hosted_domain: Optional[str] = Field(default=None, description="Google Workspace hosted domain (hd claim)")


class EmployeeRecord(BaseModel):
    """Represents a trusted corporate employee profile mapped from Google Identity."""
    employee_id: str = Field(..., description="Unique internal employee ID, e.g. EMP-2026-001")
    google_subject: str = Field(..., description="Google Subject (sub) mapping key")
    email: EmailStr
    name: str
    department: str
    team: str
    job_role: str = Field(..., description="Software Engineer, Tech Lead, Engineering Manager, etc.")
    authorization_role: AuthorizationRole = Field(default=AuthorizationRole.EMPLOYEE)
    manager_id: Optional[str] = None
    location: str = "US-Remote"
    joining_date: str = "2026-01-01"
    onboarding_status: OnboardingStatus = OnboardingStatus.IN_PROGRESS
    is_day_one: bool = False
    assigned_buddy_name: Optional[str] = None
    assigned_buddy_email: Optional[str] = None
    onboarding_track: str = "Backend"


# ============================================================================
# SESSION & CONVERSATION MODELS (PHASE C FIRESTORE INTEGRATION)
# ============================================================================

class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role: 'user', 'assistant', 'system'")
    content: str = Field(..., description="Message text content")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ActiveSessionState(BaseModel):
    """
    Persistent multi-turn session payload stored in Firestore / memory.
    Bound strictly to employee_id for anti-hijacking validation.
    """
    session_id: str = Field(..., description="Unique UUID for conversational session")
    employee_id: str = Field(..., description="Internal employee ID bound to this session")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_accessed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    conversation_history: List[ChatMessage] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# ONBOARDING MODELS
# ============================================================================

class OnboardingTask(BaseModel):
    task_id: str
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    due_days_after_start: int = 1
    completed_at: Optional[str] = None
    category: str = "Setup"
    action_link: Optional[str] = None


class OnboardingChecklist(BaseModel):
    employee_id: str
    track: str
    tasks: List[OnboardingTask]
    completed_count: int
    total_count: int
    next_pending_task: Optional[OnboardingTask] = None


class TeamMemberOnboardingProgress(BaseModel):
    employee_id: str
    name: str
    job_role: str
    team: str
    completed_count: int
    total_count: int
    pending_tasks: List[str]
    is_blocked: bool = False


class TeamOnboardingSummary(BaseModel):
    team_name: str
    manager_id: str
    manager_name: str
    total_team_members: int
    fully_onboarded_count: int
    members: List[TeamMemberOnboardingProgress]


# ============================================================================
# KNOWLEDGE MESH & RAG MODELS
# ============================================================================

class KnowledgeChunk(BaseModel):
    chunk_id: str
    document_id: str
    chunk_index: int
    content: str
    team: str = "ALL"
    access_level: AccessLevel = AccessLevel.EMPLOYEE


class KnowledgeAsset(BaseModel):
    document_id: str
    title: str
    source: str
    gcs_uri: str
    team: str = "ALL"
    access_level: AccessLevel = AccessLevel.EMPLOYEE
    document_type: str = "GUIDE"
    owner: str = "admin@company.com"
    description: str = ""
    chunks: List[KnowledgeChunk] = Field(default_factory=list)


# ============================================================================
# OPERATIONS (TIMESHEETS & INCIDENTS & ESCALATION) MODELS
# ============================================================================

class TimesheetRecord(BaseModel):
    timesheet_id: str
    employee_id: str
    period_start: str
    period_end: str
    hours_logged: float
    status: TimesheetStatus
    due_date: str


class IncidentRecord(BaseModel):
    incident_id: str
    created_by: str
    category: str
    summary: str
    severity: IncidentSeverity = IncidentSeverity.MEDIUM
    status: str = "OPEN"
    assigned_team: str = "IT-Support"
    created_at: str


class TeamEscalationContact(BaseModel):
    domain: str
    primary_lead_name: str
    primary_email: str
    primary_on_vacation: bool
    backup_lead_name: str
    backup_email: str
    backup_on_vacation: bool
    general_channel: str


# ============================================================================
# API SCHEMAS
# ============================================================================

class ChatRequest(BaseModel):
    """
    Interactive chat request.
    SECURITY: Identity is NOT accepted in the body. It is extracted securely from the Bearer token.
    """
    message: str = Field(..., min_length=1, max_length=4000, json_schema_extra={"example": "What are my pending onboarding tasks?"})
    session_id: Optional[str] = Field(default=None, description="Optional existing session ID")


class ChatResponse(BaseModel):
    response: str
    session_id: str
    agent_invoked: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    suggested_actions: List[str] = Field(default_factory=list)


class LandingResponse(BaseModel):
    employee_id: str
    name: str
    is_day_one: bool
    proactive_greeting: str
    onboarding_summary: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TaskCompletionRequest(BaseModel):
    task_id: str = Field(..., json_schema_extra={"example": "TASK-001-ENV"})


class IncidentCreateRequest(BaseModel):
    category: str = Field(..., json_schema_extra={"example": "Hardware / VPN"})
    summary: str = Field(..., min_length=5, max_length=500, json_schema_extra={"example": "Cannot connect to Cloud SQL staging VPN gateway"})
    severity: IncidentSeverity = Field(default=IncidentSeverity.MEDIUM)
    confirmed: bool = Field(default=True, description="Explicit user confirmation to create incident")
