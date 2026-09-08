export enum AuthorizationRole {
  EMPLOYEE = "employee",
  MANAGER = "manager",
  HR = "hr",
  IT = "it",
}

export enum TaskStatus {
  PENDING = "PENDING",
  IN_PROGRESS = "IN_PROGRESS",
  COMPLETED = "COMPLETED",
  BLOCKED = "BLOCKED",
}

export enum TimesheetStatus {
  SUBMITTED = "SUBMITTED",
  PENDING = "PENDING",
  OVERDUE = "OVERDUE",
  APPROVED = "APPROVED",
}

export enum IncidentSeverity {
  LOW = "LOW",
  MEDIUM = "MEDIUM",
  HIGH = "HIGH",
  CRITICAL = "CRITICAL",
}

export interface AuthenticatedPrincipal {
  subject: string;
  email: string;
  name?: string;
  issuer: string;
  audience?: string;
  hosted_domain?: string;
}

export interface EmployeeRecord {
  employee_id: string;
  google_subject: string;
  email: string;
  name: string;
  department: string;
  team: string;
  job_role: string;
  authorization_role: AuthorizationRole;
  manager_id?: string | null;
  location: string;
  joining_date: string;
  onboarding_status: string;
  is_day_one: boolean;
  assigned_buddy_name?: string | null;
  assigned_buddy_email?: string | null;
  onboarding_track: string;
}

export interface OnboardingTask {
  task_id: string;
  title: string;
  description: string;
  status: TaskStatus;
  due_days_after_start: number;
  due_date?: string;
  is_overdue?: boolean;
  completed_at?: string | null;
  category: string;
  action_link?: string | null;
}

export interface OnboardingChecklist {
  employee_id: string;
  track: string;
  tasks: OnboardingTask[];
  completed_count: number;
  total_count: number;
  next_pending_task?: OnboardingTask | null;
}

export interface TeamMemberOnboardingProgress {
  employee_id: string;
  name: string;
  job_role: string;
  team: string;
  completed_count: number;
  total_count: number;
  pending_tasks: string[];
  is_blocked: boolean;
}

export interface TeamOnboardingSummary {
  team_name: string;
  manager_id: string;
  manager_name: string;
  total_team_members: number;
  fully_onboarded_count: number;
  members: TeamMemberOnboardingProgress[];
}

export interface KnowledgeChunk {
  chunk_id: string;
  document_id: string;
  chunk_index: number;
  content: string;
  team: string;
  access_level: string;
}

export interface KnowledgeAsset {
  document_id: string;
  title: string;
  source: string;
  gcs_uri: string;
  team: string;
  access_level: string;
  document_type: string;
  owner: string;
  description: string;
  chunks: KnowledgeChunk[];
}

export interface TimesheetRecord {
  timesheet_id: string;
  employee_id: string;
  period_start: string;
  period_end: string;
  hours_logged: number;
  status: TimesheetStatus;
  due_date: string;
}

export interface IncidentRecord {
  incident_id: string;
  created_by: string;
  category: string;
  summary: string;
  severity: IncidentSeverity;
  status: string;
  assigned_team: string;
  created_at: string;
}

export interface TeamEscalationContact {
  domain: string;
  primary_lead_name: string;
  primary_email: string;
  primary_on_vacation: boolean;
  backup_lead_name: string;
  backup_email: string;
  backup_on_vacation: boolean;
  general_channel: string;
}

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
}

export interface UserSession {
  session_id: string;
  employee_id: string;
  created_at: string;
  last_accessed_at: string;
  history: ChatMessage[];
}

export interface KnowledgeMeshInsight {
  insight_id: string;
  title: string;
  category: "POLICY" | "STANDARDS" | "RUNBOOK" | "BLUEPRINT" | "SECURITY";
  summary: string;
  team: string;
  access_level: string;
  effective_date: string;
  highlight_tag: string;
  gcs_uri: string;
  action_suggestion: string;
}

