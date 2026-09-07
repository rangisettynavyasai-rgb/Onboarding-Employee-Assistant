import {
  AuthorizationRole,
  EmployeeRecord,
  IncidentRecord,
  IncidentSeverity,
  KnowledgeChunk,
  KnowledgeMeshInsight,
  OnboardingChecklist,
  TaskStatus,
  TeamEscalationContact,
  TeamMemberOnboardingProgress,
  TeamOnboardingSummary,
  TimesheetRecord,
  TimesheetStatus,
  UserSession,
} from "./types.js";
import {
  SYNTHETIC_EMPLOYEES,
  SYNTHETIC_INCIDENTS,
  SYNTHETIC_KNOWLEDGE_CATALOG,
  SYNTHETIC_KNOWLEDGE_INSIGHTS,
  SYNTHETIC_ONBOARDING_CHECKLISTS,
  SYNTHETIC_TEAM_DIRECTORY,
  SYNTHETIC_TIMESHEETS,
} from "./data.js";
import { getFirestoreDb } from "./firestore.js";


// In-memory persistent state stores
const employees: Record<string, EmployeeRecord> = { ...SYNTHETIC_EMPLOYEES };
const checklists: Record<string, OnboardingChecklist> = JSON.parse(
  JSON.stringify(SYNTHETIC_ONBOARDING_CHECKLISTS)
);
const timesheets: Record<string, TimesheetRecord[]> = JSON.parse(
  JSON.stringify(SYNTHETIC_TIMESHEETS)
);
const incidents: IncidentRecord[] = [...SYNTHETIC_INCIDENTS];
const sessions: Map<string, UserSession> = new Map();

// Helper token to employee map
const MOCK_TOKEN_MAP: Record<string, string> = {
  "mock-google-token-rahul": "EMP-2026-001",
  "mock-google-token-maya": "EMP-2026-002",
  "mock-google-token-liam": "EMP-2026-003",
  "mock-google-token-carlos": "EMP-2026-004",
  "mock-google-token-alex": "EMP-2026-005",
  "mock-google-token-priya": "EMP-2026-006",
  "mock-google-token-elena": "EMP-2026-007",
  "mock-google-token-marcus": "EMP-2026-008",
  "mock-google-token-amanda": "EMP-2026-009",
  "mock-google-token-sarah": "EMP-2026-010",
};

export class AuthService {
  static resolveEmployee(bearerToken: string): EmployeeRecord | null {
    if (!bearerToken) return null;
    const cleanToken = bearerToken.replace(/^Bearer\s+/i, "").trim();

    // 1. Direct mock token
    if (MOCK_TOKEN_MAP[cleanToken]) {
      const empId = MOCK_TOKEN_MAP[cleanToken];
      return employees[empId] || null;
    }

    // 2. Google Subject mapping (e.g. google-sub-rahul-001)
    for (const emp of Object.values(employees)) {
      if (emp.google_subject === cleanToken || emp.employee_id === cleanToken) {
        return emp;
      }
    }

    // 3. Decode Google JWT if format matches (header.payload.signature)
    if (cleanToken.includes(".")) {
      try {
        const parts = cleanToken.split(".");
        if (parts.length >= 2) {
          const payload = JSON.parse(Buffer.from(parts[1], "base64url").toString("utf-8"));
          const email = payload.email?.toLowerCase();
          const sub = payload.sub;
          const name = payload.name || email?.split("@")[0] || "Authorized Employee";

          // Match existing employee record
          for (const emp of Object.values(employees)) {
            if (emp.email.toLowerCase() === email || emp.google_subject === sub) {
              return emp;
            }
          }

          // If valid authenticated Google user not in seed list, provision employee profile
          if (email) {
            const newEmpId = `EMP-${Date.now().toString().slice(-6)}`;
            const newEmp: EmployeeRecord = {
              employee_id: newEmpId,
              google_subject: sub || `sub-${Date.now()}`,
              email: email,
              name: name,
              department: "Engineering",
              team: "Payments",
              job_role: "Engineer",
              authorization_role: AuthorizationRole.EMPLOYEE,
              manager_id: "EMP-2026-010",
              location: "Remote",
              joining_date: new Date().toISOString().split("T")[0],
              onboarding_status: "IN_PROGRESS",
              is_day_one: false,
              assigned_buddy_name: "Priya Nair",
              assigned_buddy_email: "priya.nair@company.com",
              onboarding_track: "Backend",
            };
            employees[newEmpId] = newEmp;
            return newEmp;
          }
        }
      } catch {
        // invalid jwt
      }
    }

    // 4. Match direct email string or employee_id string directly
    const directSearch = cleanToken.toLowerCase();
    for (const emp of Object.values(employees)) {
      if (emp.email.toLowerCase() === directSearch || emp.employee_id.toLowerCase() === directSearch) {
        return emp;
      }
    }

    // 5. If user provides arbitrary email (e.g. from enterprise corporate login)
    if (directSearch.includes("@")) {
      const newEmpId = `EMP-${Date.now().toString().slice(-6)}`;
      const prefix = directSearch.split("@")[0];
      const displayName = prefix.charAt(0).toUpperCase() + prefix.slice(1);
      const newEmp: EmployeeRecord = {
        employee_id: newEmpId,
        google_subject: `sub-${directSearch}`,
        email: directSearch,
        name: displayName,
        department: "Engineering",
        team: "Payments",
        job_role: "Software Engineer",
        authorization_role: AuthorizationRole.EMPLOYEE,
        manager_id: "EMP-2026-010",
        location: "HQ",
        joining_date: new Date().toISOString().split("T")[0],
        onboarding_status: "IN_PROGRESS",
        is_day_one: false,
        assigned_buddy_name: "Priya Nair",
        assigned_buddy_email: "priya.nair@company.com",
        onboarding_track: "Backend",
      };
      employees[newEmpId] = newEmp;
      return newEmp;
    }

    // Default demo fallback if token starts with mock-google
    return employees["EMP-2026-001"] || null;
  }
}


export class OnboardingService {
  static getChecklist(employeeId: string): OnboardingChecklist | null {
    return checklists[employeeId] || null;
  }

  static completeTask(employeeId: string, taskId: string): boolean {
    const cl = checklists[employeeId];
    if (!cl) return false;
    const task = cl.tasks.find((t) => t.task_id === taskId);
    if (!task) return false;

    task.status = TaskStatus.COMPLETED;
    task.completed_at = new Date().toISOString();
    cl.completed_count = cl.tasks.filter((t) => t.status === TaskStatus.COMPLETED).length;
    cl.next_pending_task = cl.tasks.find((t) => t.status === TaskStatus.PENDING) || null;
    return true;
  }

  static getTeamProgress(manager: EmployeeRecord): TeamOnboardingSummary {
    const directReports = Object.values(employees).filter(
      (e) => e.manager_id === manager.employee_id || e.team === manager.team
    );

    const members: TeamMemberOnboardingProgress[] = directReports.map((report) => {
      const cl = checklists[report.employee_id];
      const completed = cl ? cl.completed_count : 0;
      const total = cl ? cl.total_count : 0;
      const pending = cl
        ? cl.tasks.filter((t) => t.status !== TaskStatus.COMPLETED).map((t) => t.title)
        : [];
      return {
        employee_id: report.employee_id,
        name: report.name,
        job_role: report.job_role,
        team: report.team,
        completed_count: completed,
        total_count: total,
        pending_tasks: pending,
        is_blocked: false,
      };
    });

    const fullyOnboarded = members.filter((m) => m.completed_count >= m.total_count && m.total_count > 0).length;

    return {
      team_name: manager.team,
      manager_id: manager.employee_id,
      manager_name: manager.name,
      total_team_members: members.length,
      fully_onboarded_count: fullyOnboarded,
      members,
    };
  }
}

export class OperationsService {
  static getTimesheetStatus(employeeId: string) {
    const records = timesheets[employeeId] || [];
    if (records.length === 0) {
      return {
        employee_id: employeeId,
        period: "Current Cycle",
        hours_logged: 40.0,
        status: TimesheetStatus.APPROVED,
        action_required: false,
        message: "Your timesheet is fully approved and up to date.",
      };
    }
    const latest = records[0];
    const actionRequired =
      latest.status === TimesheetStatus.PENDING || latest.status === TimesheetStatus.OVERDUE;
    return {
      employee_id: employeeId,
      period: `${latest.period_start} to ${latest.period_end}`,
      period_end: latest.period_end,
      hours_logged: latest.hours_logged,
      status: latest.status,
      due_date: latest.due_date,
      action_required: actionRequired,
      message: actionRequired
        ? `Your timesheet for week ending ${latest.period_end} is currently ${latest.status} (${latest.hours_logged} hours logged). Please submit before Friday 5:00 PM.`
        : `Your timesheet for week ending ${latest.period_end} is ${latest.status}.`,
    };
  }

  static createIncident(
    actor: EmployeeRecord,
    category: string,
    summary: string,
    severity: IncidentSeverity = IncidentSeverity.MEDIUM
  ): IncidentRecord {
    const incidentId = `INC-2026-${Math.random().toString(36).substring(2, 8).toUpperCase()}`;
    const assignedTeam =
      category.toLowerCase().includes("sql") ||
      category.toLowerCase().includes("database") ||
      category.toLowerCase().includes("k8s")
        ? "Platform"
        : "IT-Support";

    const record: IncidentRecord = {
      incident_id: incidentId,
      created_by: actor.employee_id,
      category,
      summary,
      severity,
      status: "OPEN",
      assigned_team: assignedTeam,
      created_at: new Date().toISOString(),
    };
    incidents.push(record);
    return record;
  }

  static resolveEscalation(domain: string): {
    domain: string;
    status: string;
    assigned_contact: string;
    channel: string;
    message: string;
  } {
    const contact = SYNTHETIC_TEAM_DIRECTORY[domain];
    if (!contact) {
      return {
        domain,
        status: "FALLBACK_GENERAL",
        assigned_contact: "IT Service Desk",
        channel: "#general-it-helpdesk",
        message: `No specific point-of-contact registered for '${domain}'. Routed to #general-it-helpdesk.`,
      };
    }

    if (!contact.primary_on_vacation) {
      return {
        domain,
        status: "PRIMARY_ASSIGNED",
        assigned_contact: `${contact.primary_lead_name} (${contact.primary_email})`,
        channel: contact.general_channel,
        message: `Assigned to Primary Lead: ${contact.primary_lead_name} (${contact.primary_email}). Available on Slack.`,
      };
    }

    if (contact.primary_on_vacation && !contact.backup_on_vacation) {
      return {
        domain,
        status: "BACKUP_ASSIGNED",
        assigned_contact: `${contact.backup_lead_name} (${contact.backup_email})`,
        channel: contact.general_channel,
        message: `Primary Lead (${contact.primary_lead_name}) is Out of Office. Re-routed to Backup Lead: ${contact.backup_lead_name} (${contact.backup_email}).`,
      };
    }

    return {
      domain,
      status: "BOTH_OOO_BROADCAST_TRIGGERED",
      assigned_contact: `Broadcast Channel (${contact.general_channel})`,
      channel: contact.general_channel,
      message: `High Priority Alert: Both Primary (${contact.primary_lead_name}) and Backup (${contact.backup_lead_name}) leads are Out of Office. Ticket broadcasted to ${contact.general_channel}.`,
    };
  }
}

export class KnowledgeService {
  static searchAuthorized(actor: EmployeeRecord, query: string): KnowledgeChunk[] {
    const q = query.toLowerCase();
    const results: KnowledgeChunk[] = [];

    const isManagerOrHR =
      actor.authorization_role === AuthorizationRole.MANAGER ||
      actor.authorization_role === AuthorizationRole.HR;

    for (const asset of Object.values(SYNTHETIC_KNOWLEDGE_CATALOG)) {
      // Access clearance check
      if (asset.access_level === "manager" && !isManagerOrHR) {
        continue;
      }
      // Team domain check
      if (asset.team !== "ALL" && asset.team.toLowerCase() !== actor.team.toLowerCase()) {
        continue;
      }

      const words = q.split(/\s+/).filter(w => w.length > 2);
      for (const chunk of asset.chunks) {
        const matchesDirect =
          asset.title.toLowerCase().includes(q) ||
          chunk.content.toLowerCase().includes(q) ||
          (asset.description && asset.description.toLowerCase().includes(q)) ||
          q.includes(asset.team.toLowerCase()) ||
          q.includes("runbook") ||
          q.includes("doc") ||
          q.includes("standard") ||
          words.some(w => 
            asset.title.toLowerCase().includes(w) || 
            chunk.content.toLowerCase().includes(w) ||
            (asset.description && asset.description.toLowerCase().includes(w))
          );

        if (matchesDirect) {
          results.push(chunk);
        }
      }
    }
    return results;
  }

  static formatContext(actor: EmployeeRecord, chunks: KnowledgeChunk[], query?: string): string {
    const perimeterStamp = `[ENFORCED_SECURITY_PERIMETER: employee_id=${actor.employee_id} | department=${actor.department} | team=${actor.team} | clearance=${actor.authorization_role}]`;
    if (chunks.length === 0) {
      return `${perimeterStamp}\nNo authorized company knowledge assets matched your query.`;
    }
    const lines = [perimeterStamp];
    if (query) lines.push(`Search Query: ${query}`);
    chunks.forEach((chunk, i) => {
      lines.push(
        `--- [AUTHORIZED ASSET ${i + 1} | ID: ${chunk.document_id}] ---\nTeam Domain: ${chunk.team} | Clearance Level: ${chunk.access_level}\n${chunk.content}\n`
      );
    });
    return lines.join("\n");
  }

  static getAuthorizedInsights(actor: EmployeeRecord): KnowledgeMeshInsight[] {
    const isManagerOrHR =
      actor.authorization_role === AuthorizationRole.MANAGER ||
      actor.authorization_role === AuthorizationRole.HR;

    return SYNTHETIC_KNOWLEDGE_INSIGHTS.filter((insight) => {
      if (insight.access_level === "manager" && !isManagerOrHR) {
        return false;
      }
      if (insight.team !== "ALL" && insight.team.toLowerCase() !== actor.team.toLowerCase()) {
        return false;
      }
      return true;
    });
  }
}


export class ProactiveService {
  static generateLanding(employee: EmployeeRecord) {
    const checklist = OnboardingService.getChecklist(employee.employee_id);
    const timesheetInfo = OperationsService.getTimesheetStatus(employee.employee_id);

    let greeting = "";
    if (employee.is_day_one) {
      const gcsFolder = `gs://patchamomma-knowledge-mesh/onboarding/${employee.team.toLowerCase()}`;
      const nextTaskText = checklist?.next_pending_task
        ? `Your next task is: **${checklist.next_pending_task.title}**`
        : "All Day 1 tasks are initialized.";

      greeting =
        `🎉 **Welcome to Patchamomma 2026, ${employee.name}! (Day 1 Onboarding Kickoff)**\n\n` +
        `We are thrilled to welcome you to the **${employee.team}** team as a **${employee.job_role}**.\n\n` +
        `### 🚀 Your Day 1 Orientation Kit:\n` +
        `1. **Onboarding Status**: Completed ${checklist ? checklist.completed_count : 0} of ${checklist ? checklist.total_count : 4} tasks.\n` +
        `   - ${nextTaskText}\n` +
        `2. **Team Knowledge Mesh Docs**:\n` +
        `   - [\`${gcsFolder}/day1_getting_started.pdf\`](${gcsFolder}/day1_getting_started.pdf)\n` +
        `   - [\`${gcsFolder}/architecture_overview_2026.md\`](${gcsFolder}/architecture_overview_2026.md)\n` +
        `3. **Walkthrough Video Asset**:\n` +
        `   - Link: \`gs://patchamomma-knowledge-mesh/videos/onboarding/${employee.onboarding_track.toLowerCase()}_deepdive.mp4\`\n` +
        `   - ⏱️ **Key Timestamp**: Skip to **Minute 04:15** for environment setup and **Minute 18:45** for Cloud SQL Proxy setup.\n` +
        `4. **Your Onboarding Buddy**:\n` +
        `   - **${employee.assigned_buddy_name || "Priya Nair"}** (${employee.assigned_buddy_email || "priya.nair@company.com"}) - Reach out anytime!\n\n` +
        `Ask me anything about setup, code standards, or company documentation!`;
    } else {
      const completedStr =
        checklist && checklist.completed_count < checklist.total_count
          ? `You have completed ${checklist.completed_count} of ${checklist.total_count} onboarding tasks.`
          : "All onboarding tasks completed.";
      const tsReminder = timesheetInfo.action_required
        ? `\n⚠️ *Reminder*: ${timesheetInfo.message}`
        : "";

      greeting =
        `👋 Welcome back, **${employee.name}** (${employee.job_role}, ${employee.team}).\n` +
        `${completedStr}${tsReminder}\n` +
        `How can I assist your workflow or codebase questions today?`;
    }

    return {
      employee_id: employee.employee_id,
      name: employee.name,
      is_day_one: employee.is_day_one,
      proactive_greeting: greeting,
      onboarding_summary: checklist,
      timesheet_status: timesheetInfo,
      timestamp: new Date().toISOString(),
    };
  }
}

export class SessionService {
  static async getOrCreateSession(employeeId: string, sessionId?: string): Promise<UserSession> {
    const db = getFirestoreDb();
    const effectiveId = sessionId || `sess-${employeeId.toLowerCase()}-${Date.now().toString(36)}`;

    // 1. Check local cache
    if (sessions.has(effectiveId)) {
      const sess = sessions.get(effectiveId)!;
      if (sess.employee_id === employeeId) {
        sess.last_accessed_at = new Date().toISOString();
        return sess;
      }
    }

    // 2. Check Firestore if database is available
    if (db) {
      try {
        const docRef = db.collection("sessions").doc(effectiveId);
        const snapshot = await docRef.get();
        if (snapshot.exists) {
          const data = snapshot.data() as UserSession;
          if (data && data.employee_id === employeeId) {
            data.last_accessed_at = new Date().toISOString();
            sessions.set(effectiveId, data);
            // Async touch last_accessed_at
            docRef.update({ last_accessed_at: data.last_accessed_at }).catch(() => {});
            return data;
          }
        }
      } catch (err) {
        console.warn(`Firestore read failed for session ${effectiveId}, falling back to memory:`, err);
      }
    }

    // 3. Create fresh session
    const newSession: UserSession = {
      session_id: effectiveId,
      employee_id: employeeId,
      created_at: new Date().toISOString(),
      last_accessed_at: new Date().toISOString(),
      history: [],
    };
    sessions.set(effectiveId, newSession);

    if (db) {
      db.collection("sessions").doc(effectiveId).set(newSession).catch((err) => {
        console.warn(`Firestore initial write failed for session ${effectiveId}:`, err);
      });
    }

    return newSession;
  }

  static async saveSession(session: UserSession): Promise<void> {
    session.last_accessed_at = new Date().toISOString();
    sessions.set(session.session_id, session);

    const db = getFirestoreDb();
    if (db) {
      try {
        await db.collection("sessions").doc(session.session_id).set(session, { merge: true });
      } catch (err) {
        console.warn(`Firestore sync failed for session ${session.session_id}:`, err);
      }
    }
  }

  static getSessionSync(employeeId: string, sessionId?: string): UserSession {
    const effectiveId = sessionId || `sess-${employeeId.toLowerCase()}`;
    if (sessions.has(effectiveId)) {
      const sess = sessions.get(effectiveId)!;
      if (sess.employee_id === employeeId) {
        sess.last_accessed_at = new Date().toISOString();
        return sess;
      }
    }
    const fallback: UserSession = {
      session_id: effectiveId,
      employee_id: employeeId,
      created_at: new Date().toISOString(),
      last_accessed_at: new Date().toISOString(),
      history: [],
    };
    sessions.set(effectiveId, fallback);
    return fallback;
  }
}

