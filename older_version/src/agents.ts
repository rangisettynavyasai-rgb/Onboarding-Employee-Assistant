import { GoogleGenAI } from "@google/genai";
import { EmployeeRecord, IncidentSeverity } from "./types.js";
import {
  KnowledgeService,
  OnboardingService,
  OperationsService,
} from "./services.js";

let genaiClient: GoogleGenAI | null = null;

function getGeminiClient(): GoogleGenAI | null {
  if (!genaiClient && process.env.GEMINI_API_KEY) {
    try {
      genaiClient = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });
    } catch {
      genaiClient = null;
    }
  }
  return genaiClient;
}

export interface AgentResult {
  response: string;
  agent_invoked: string;
  suggested_actions: string[];
}

export class OnboardingAgent {
  static handle(actor: EmployeeRecord, message: string): AgentResult {
    const lower = message.toLowerCase();
    const checklist = OnboardingService.getChecklist(actor.employee_id);

    if (lower.includes("team") && (lower.includes("progress") || lower.includes("member"))) {
      const summary = OnboardingService.getTeamProgress(actor);
      const membersStr = summary.members
        .map(
          (m) =>
            `- **${m.name}** (${m.job_role}): ${m.completed_count}/${m.total_count} tasks completed`
        )
        .join("\n");
      return {
        response:
          `📋 **Team Onboarding Rollup (${summary.team_name})**\n\n` +
          `Manager: **${summary.manager_name}**\n` +
          `Total Team Members: ${summary.total_team_members} | Fully Onboarded: ${summary.fully_onboarded_count}\n\n` +
          `${membersStr}`,
        agent_invoked: "Onboarding Specialist",
        suggested_actions: ["View Pending Tasks", "Search Runbooks"],
      };
    }

    if (lower.includes("buddy") || lower.includes("mentor") || lower.includes("priya") || lower.includes("david")) {
      const buddyName = actor.assigned_buddy_name || "Priya Nair";
      const buddyEmail = actor.assigned_buddy_email || "priya.nair@company.com";
      return {
        response:
          `🤝 **Your Assigned Onboarding Buddy is ${buddyName}**\n\n` +
          `Email: [${buddyEmail}](mailto:${buddyEmail})\n` +
          `Team: ${actor.team}\n\n` +
          `Feel free to reach out to schedule an intro 1:1, ask architecture questions, or request code reviews!`,
        agent_invoked: "Onboarding Specialist",
        suggested_actions: ["View Pending Tasks", "Coding Standards"],
      };
    }

    if (!checklist) {
      return {
        response: `All onboarding requirements for **${actor.name}** are completed. You are fully ramped up!`,
        agent_invoked: "Onboarding Specialist",
        suggested_actions: ["Check Timesheet", "Search Runbooks"],
      };
    }

    const pendingList = checklist.tasks
      .filter((t) => t.status !== "COMPLETED")
      .map((t) => `- **${t.title}** (\`${t.task_id}\`) - ${t.category}: ${t.description}`)
      .join("\n");

    return {
      response:
        `📋 **Onboarding Progress for ${actor.name}** (${checklist.completed_count}/${checklist.total_count} Completed)\n\n` +
        `**Pending Action Items:**\n${pendingList || "No pending items! All tasks complete."}\n\n` +
        (checklist.next_pending_task
          ? `👉 **Next Priority**: ${checklist.next_pending_task.title}`
          : "🎉 All Day 1 milestones cleared!"),
      agent_invoked: "Onboarding Specialist",
      suggested_actions: ["Check Timesheet", "Coding Standards", "Search Runbooks"],
    };
  }
}

export class OperationsAgent {
  static handle(actor: EmployeeRecord, message: string): AgentResult {
    const lower = message.toLowerCase();

    // 1. Timesheet Queries
    if (lower.includes("timesheet") || lower.includes("hours") || lower.includes("friday")) {
      const ts = OperationsService.getTimesheetStatus(actor.employee_id);
      return {
        response:
          `⏱️ **Timesheet Status (${ts.period})**\n\n` +
          `- **Status**: \`${ts.status}\`\n` +
          `- **Logged Hours**: ${ts.hours_logged}\n` +
          `- **Due Date**: ${ts.due_date || "End of week"}\n\n` +
          `${ts.message}`,
        agent_invoked: "Operations Agent",
        suggested_actions: ["View Pending Tasks", "Report IT Ticket"],
      };
    }

    // 2. Escalation & Lead Lookups
    if (
      lower.includes("lead") ||
      lower.includes("escalat") ||
      lower.includes("contact") ||
      lower.includes("on call") ||
      lower.includes("who to contact") ||
      lower.includes("blocker")
    ) {
      let domain = "Cloud SQL";
      if (lower.includes("kube") || lower.includes("k8s") || lower.includes("cluster")) {
        domain = "Kubernetes";
      } else if (lower.includes("iam") || lower.includes("security") || lower.includes("permission")) {
        domain = "IAM & Security";
      } else if (lower.includes("data") || lower.includes("pipeline") || lower.includes("bigquery")) {
        domain = "Data Pipelines";
      }

      const esc = OperationsService.resolveEscalation(domain);
      return {
        response:
          `📞 **Escalation Routing for ${esc.domain}**\n\n` +
          `- **Status**: \`${esc.status}\`\n` +
          `- **Assigned Contact**: ${esc.assigned_contact}\n` +
          `- **Channel**: \`${esc.channel}\`\n\n` +
          `${esc.message}`,
        agent_invoked: "Operations Agent",
        suggested_actions: ["Report IT Ticket", "Search Runbooks"],
      };
    }

    // 3. Incident Creation request
    if (lower.includes("incident") || lower.includes("ticket") || lower.includes("broken") || lower.includes("down")) {
      const category = lower.includes("sql") ? "Cloud SQL / Database Access" : "Platform / General";
      const inc = OperationsService.createIncident(
        actor,
        category,
        message,
        IncidentSeverity.MEDIUM
      );
      return {
        response:
          `🚨 **Incident Ticket Dispatched**\n\n` +
          `- **Ticket ID**: \`${inc.incident_id}\`\n` +
          `- **Category**: ${inc.category}\n` +
          `- **Assigned Team**: ${inc.assigned_team}\n` +
          `- **Status**: ${inc.status}\n\n` +
          `The on-call team has been alerted via telemetry streaming.`,
        agent_invoked: "Operations Agent",
        suggested_actions: ["Check Timesheet", "Search Runbooks"],
      };
    }

    const defaultTs = OperationsService.getTimesheetStatus(actor.employee_id);
    return {
      response: `Operations status: ${defaultTs.message}`,
      agent_invoked: "Operations Agent",
      suggested_actions: ["Check Timesheet", "Report IT Ticket"],
    };
  }
}

export class KnowledgeAgent {
  static handle(actor: EmployeeRecord, message: string): AgentResult {
    const chunks = KnowledgeService.searchAuthorized(actor, message);
    const formattedContext = KnowledgeService.formatContext(actor, chunks, message);

    if (chunks.length === 0) {
      return {
        response:
          `🔍 **Knowledge Mesh Search**\n\n` +
          `No authorized internal documentation found matching "${message}".\n\n` +
          `*Note*: Access to managerial documents is restricted to Managers and HR. Team-specific runbooks are scoped to your team (${actor.team}) and ALL.`,
        agent_invoked: "Knowledge Mesh Agent",
        suggested_actions: ["Coding Standards", "View Pending Tasks"],
      };
    }

    const docSummaries = chunks
      .map((c) => `### 📄 ${c.document_id} (Domain: ${c.team})\n${c.content}`)
      .join("\n\n");

    return {
      response:
        `📚 **Knowledge Mesh Results (Authorized Pre-Retrieval Filter)**\n\n` +
        `Security Clearance: \`${actor.authorization_role}\` | Team: \`${actor.team}\`\n\n` +
        `${docSummaries}`,
      agent_invoked: "Knowledge Mesh Agent",
      suggested_actions: ["Coding Standards", "Check Timesheet"],
    };
  }
}

export class CodeMentorAgent {
  static handle(actor: EmployeeRecord, message: string): AgentResult {
    const lower = message.toLowerCase();

    if (lower.includes("print") || lower.includes("log") || lower.includes("standard")) {
      return {
        response:
          `💻 **Corporate Coding & Logging Standards 2026**\n\n` +
          `1. **Zero Raw Print Policy**: Never commit raw \`print(...)\` statements. All services must use structured JSON logs with correlation IDs:\n` +
          `\`\`\`typescript\n` +
          `logger.info({ event: "PAYMENT_PROCESSED", user_id: employee_id, status: "SUCCESS" });\n` +
          `\`\`\`\n` +
          `2. **Cloud SQL Proxy**: Connect via 127.0.0.1:5432 using IAM database authentication, never hardcoded credentials.\n` +
          `3. **Idempotency**: All payment mutative endpoints require an \`Idempotency-Key\` HTTP header.`,
        agent_invoked: "Code Mentor Agent",
        suggested_actions: ["Search Runbooks", "View Pending Tasks"],
      };
    }

    return {
      response:
        `💻 **Code Mentor Architecture Guidance**\n\n` +
        `Our backend microservices follow clean hexagonal architecture with:\n` +
        `- Google Cloud Run stateless container deployment\n` +
        `- Cloud SQL Postgres with IAM Auth proxy\n` +
        `- Strict TypeScript/Python type enforcement and JSON structured logging.\n\n` +
        `Would you like to review our database setup or local proxy configuration?`,
      agent_invoked: "Code Mentor Agent",
      suggested_actions: ["Coding Standards", "Search Runbooks"],
    };
  }
}

export class SupervisorAgent {
  static async orchestrate(actor: EmployeeRecord, message: string): Promise<AgentResult> {
    const lower = message.toLowerCase();

    // Intent Routing
    let targetAgent: "operations" | "knowledge" | "code" | "onboarding" = "onboarding";

    if (
      lower.includes("timesheet") ||
      lower.includes("incident") ||
      lower.includes("ticket") ||
      lower.includes("blocker") ||
      lower.includes("escalat") ||
      lower.includes("lead") ||
      lower.includes("hours")
    ) {
      targetAgent = "operations";
    } else if (
      lower.includes("code") ||
      lower.includes("log") ||
      lower.includes("print") ||
      lower.includes("lint") ||
      lower.includes("standard") ||
      lower.includes("proxy")
    ) {
      targetAgent = "code";
    } else if (
      lower.includes("doc") ||
      lower.includes("runbook") ||
      lower.includes("manual") ||
      lower.includes("policy") ||
      lower.includes("conduct") ||
      lower.includes("search") ||
      lower.includes("mesh") ||
      lower.includes("compensation")
    ) {
      targetAgent = "knowledge";
    } else {
      targetAgent = "onboarding";
    }

    // Attempt Gemini synthesis if API key is available
    const gemini = getGeminiClient();
    if (gemini) {
      try {
        const chunks = KnowledgeService.searchAuthorized(actor, message);
        const contextStr = KnowledgeService.formatContext(actor, chunks, message);
        const checklist = OnboardingService.getChecklist(actor.employee_id);

        const prompt =
          `You are the Patchamomma Enterprise AI Assistant for Google Cloud.\n` +
          `User: ${actor.name} (${actor.job_role}, ${actor.team}, Role: ${actor.authorization_role}).\n` +
          `Day-1 Onboarding Status: ${actor.is_day_one ? "Day 1" : "Ramped"}.\n` +
          `Checklist summary: ${checklist ? `${checklist.completed_count}/${checklist.total_count} tasks completed` : "All complete"}.\n` +
          `Internal Knowledge Context:\n${contextStr}\n\n` +
          `User Message: "${message}"\n\n` +
          `Provide a clear, professional, concise, and helpful response grounded strictly in the provided context and company policies. Do not hallucinate external policies.`;

        const response = await gemini.models.generateContent({
          model: "gemini-2.5-flash",
          contents: prompt,
        });

        if (response.text) {
          return {
            response: response.text,
            agent_invoked: `Supervisor AI (${targetAgent.toUpperCase()})`,
            suggested_actions: ["Check Timesheet", "View Pending Tasks", "Search Runbooks"],
          };
        }
      } catch (err) {
        console.warn("Gemini generation fallback:", err);
      }
    }

    // Sub-agent deterministic fallback
    switch (targetAgent) {
      case "operations":
        return OperationsAgent.handle(actor, message);
      case "code":
        return CodeMentorAgent.handle(actor, message);
      case "knowledge":
        return KnowledgeAgent.handle(actor, message);
      case "onboarding":
      default:
        return OnboardingAgent.handle(actor, message);
    }
  }
}
