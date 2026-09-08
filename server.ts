import dotenv from "dotenv";
dotenv.config();

import express, { Request, Response, NextFunction } from "express";
import cors from "cors";
import path from "path";
import fs from "fs";
import { GoogleGenAI } from "@google/genai";
import { callPythonBackend } from "./src/pythonBridge.js";

// Load non-secret configuration from app.config.json if available
try {
  const configPath = path.join(process.cwd(), "app.config.json");
  if (fs.existsSync(configPath)) {
    const appConfig = JSON.parse(fs.readFileSync(configPath, "utf-8"));
    const setIfMissing = (key: string, val: any) => {
      if (val && !process.env[key]) process.env[key] = String(val);
    };
    setIfMissing("ENVIRONMENT", appConfig.environment);
    setIfMissing("ALLOWED_CORPORATE_DOMAIN", appConfig.allowedCorporateDomain);
    setIfMissing("GCP_PROJECT_ID", appConfig.gcpProjectId);
    setIfMissing("FIREBASE_PROJECT_ID", appConfig.gcpProjectId);
    setIfMissing("FIRESTORE_DATABASE_ID", appConfig.firestoreDatabaseId);
    setIfMissing("GOOGLE_OAUTH_CLIENT_ID", appConfig.googleOAuthClientId);
    setIfMissing("JIRA_HOST", appConfig.jira?.host);
    setIfMissing("JIRA_PROJECT_KEY", appConfig.jira?.projectKey);
    setIfMissing("SALESFORCE_INSTANCE_URL", appConfig.salesforce?.instanceUrl);
  }
} catch (e) {
  console.warn("[Config] Notice: Could not parse app.config.json:", e);
}

const app = express();
const PORT = 3000;

app.use(cors());
app.use(express.json());

// Extend express Request to hold authenticated employee context from Python
export interface AuthenticatedEmployee {
  employee_id: string;
  name?: string;
  email?: string;
  department?: string;
  team?: string;
  job_role?: string;
  authorization_role?: string;
  [key: string]: any;
}

interface AuthenticatedRequest extends Request {
  employee?: AuthenticatedEmployee;
}

// Authentication Middleware powered by Python Backend AuthService
async function requireAuth(req: AuthenticatedRequest, res: Response, next: NextFunction) {
  const authHeader = req.headers.authorization;
  if (!authHeader) {
    res.status(401).json({ detail: "Missing Authorization Bearer header." });
    return;
  }

  try {
    const pyAuth = await callPythonBackend({
      action: "resolve_employee",
      identity: authHeader,
    });

    if (!pyAuth || pyAuth.error || !pyAuth.employee) {
      res.status(401).json({ detail: "Invalid or expired Google Identity token." });
      return;
    }

    req.employee = pyAuth.employee;
    next();
  } catch (err: any) {
    res.status(401).json({ detail: "Authentication verification error: " + err.message });
  }
}

// 1. Health Check
app.get("/health", async (_req, res) => {
  try {
    const pyHealth = await callPythonBackend({ action: "health" });
    res.json({
      status: "ok",
      service: "Onboarding-Employee-Assistant-Gateway",
      python_backend: pyHealth,
      timestamp: new Date().toISOString(),
    });
  } catch (e: any) {
    res.json({
      status: "degraded",
      error: e.message,
      timestamp: new Date().toISOString(),
    });
  }
});

// 1b. Direct Employee Sign-In (Corporate Directory & Password)
app.post("/api/v1/auth/login", async (req, res) => {
  const { identity, password } = req.body;
  if (!identity || typeof identity !== "string") {
    res.status(400).json({ detail: "Work Email or Employee ID is required." });
    return;
  }

  try {
    const pyLogin = await callPythonBackend({
      action: "login",
      identity,
      password: typeof password === "string" ? password : "",
    });

    if (!pyLogin || pyLogin.error || !pyLogin.employee) {
      res.status(401).json({ detail: pyLogin?.error || "Invalid employee credentials or identity not found." });
      return;
    }

    res.json({
      status: "authenticated",
      token: pyLogin.token || identity,
      employee: pyLogin.employee,
    });
  } catch (err: any) {
    res.status(500).json({ detail: err.message || "Authentication service error" });
  }
});

// 1c. Google Identity Services (GIS) / Corporate Google Workspace Authentication
app.post("/api/v1/auth/google", async (req, res) => {
  const { credential, email, name, sub } = req.body;
  if (!credential && !email) {
    res.status(400).json({ detail: "Google credential or email is required." });
    return;
  }

  try {
    let resolvedEmail = (typeof email === "string" ? email.trim() : "") || "";
    let resolvedName = (typeof name === "string" ? name.trim() : "") || "";
    let resolvedSub = (typeof sub === "string" ? sub.trim() : "") || "";

    // 1. If credential is an OAuth access token (starts with ya29.)
    if (typeof credential === "string" && credential.startsWith("ya29.")) {
      try {
        const userinfoRes = await fetch("https://www.googleapis.com/oauth2/v3/userinfo", {
          headers: { Authorization: `Bearer ${credential}` },
        });
        if (userinfoRes.ok) {
          const userinfo: any = await userinfoRes.json();
          if (userinfo.email) resolvedEmail = userinfo.email;
          if (userinfo.name) resolvedName = userinfo.name;
          if (userinfo.sub) resolvedSub = userinfo.sub;
        }
      } catch (oauthErr) {
        console.warn("Could not fetch userinfo from Google OAuth access token:", oauthErr);
      }
    }

    // 2. If a true Google JWT ID token credential is provided (exactly 3 dot-separated parts starting with eyJ)
    const isJwt =
      typeof credential === "string" &&
      !credential.includes("@") &&
      credential.split(".").length === 3 &&
      credential.startsWith("eyJ");

    if (isJwt) {
      try {
        const parts = credential.split(".");
        let payloadBase64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
        while (payloadBase64.length % 4 !== 0) {
          payloadBase64 += "=";
        }
        const payloadJson = Buffer.from(payloadBase64, "base64").toString("utf-8");
        const claims = JSON.parse(payloadJson);
        if (claims.email) resolvedEmail = claims.email;
        if (claims.name) resolvedName = claims.name;
        if (claims.sub) resolvedSub = claims.sub;
      } catch (decodeErr) {
        console.warn("Could not decode Google ID token payload:", decodeErr);
      }
    }

    // 3. If credential itself is directly an email address
    if (!resolvedEmail && typeof credential === "string" && credential.includes("@")) {
      resolvedEmail = credential.trim();
    }

    const pyAuth = await callPythonBackend({
      action: "register_google_profile",
      email: resolvedEmail || credential || "",
      name: resolvedName || "",
      sub: resolvedSub || "",
      identity: resolvedEmail || credential || "",
    });

    if (!pyAuth || pyAuth.error) {
      res.status(401).json({ detail: pyAuth?.error || "Google Identity authentication failed." });
      return;
    }

    res.json({
      status: "authenticated",
      token: pyAuth.employee_id || resolvedEmail || credential,
      employee: pyAuth,
    });
  } catch (err: any) {
    res.status(500).json({ detail: err.message || "Google authentication service error" });
  }
});

// 2. Proactive Landing Screen
app.post("/api/v1/landing", requireAuth, async (req: AuthenticatedRequest, res) => {
  try {
    const landing = await callPythonBackend({
      action: "landing",
      identity: req.employee!.employee_id,
    });
    res.json(landing);
  } catch (err: any) {
    res.status(500).json({ detail: err.message || "Failed to generate landing" });
  }
});

// 3. Conversational Multi-Agent Hub (Powered by Gemini 3.6 Flash with Python Mesh Grounding)
app.post("/api/v1/chat", requireAuth, async (req: AuthenticatedRequest, res) => {
  try {
    const { message, session_id } = req.body;
    if (!message || typeof message !== "string") {
      res.status(400).json({ detail: "Message is required." });
      return;
    }

    const employee = req.employee!;
    let contextChunks = "";
    let checklistInfo = "";
    try {
      const [searchRes, checklistRes] = await Promise.all([
        callPythonBackend({
          action: "search_knowledge",
          identity: employee.employee_id,
          query: message,
        }),
        callPythonBackend({
          action: "get_checklist",
          identity: employee.employee_id,
        }),
      ]);

      if (searchRes && searchRes.context) {
        contextChunks = searchRes.context;
      }
      if (checklistRes && checklistRes.tasks) {
        const pending = checklistRes.tasks.filter((t: any) => t.status !== "COMPLETED");
        checklistInfo = `Onboarding Tasks: ${checklistRes.completed_count}/${checklistRes.total_count} completed. Next pending: ${pending.map((p: any) => p.title + " (" + p.task_id + ")").join(", ") || "None"}.`;
      }
    } catch (fetchErr: any) {
      console.warn("Context fetch notice:", fetchErr.message);
    }

    if (process.env.GEMINI_API_KEY) {
      try {
        const ai = new GoogleGenAI();
        const systemPrompt = `You are the Company AI Assistant, an internal workplace assistant helping employees with onboarding, company runbooks, engineering standards, and daily operations.

Employee Profile:
- Name: ${employee.name || "Employee"}
- ID: ${employee.employee_id}
- Role: ${employee.job_role || "Team Member"}
- Team: ${employee.team || "Engineering"}
- Authorization Clearance: ${employee.authorization_role || "employee"}
${checklistInfo}

Company Operational Standards & Policies:
- Core collaboration hours: 10:00 AM – 4:00 PM local time.
- Weekly timesheets: Due every Friday by 5:00 PM for automated payroll processing.
- Engineering Coding Standards: Zero raw print policy (never commit raw print or console.log). RFC-5424 structured JSON logging required. Cloud SQL Auth Proxy sidecar via 127.0.0.1:5432 with IAM authentication. Idempotency-Key headers required on mutable payment endpoints with 24-hour Redis TTL. Conventional Commits strictly enforced.
- IT Support & Escalations: 3-tier routing: Primary Lead, Backup Lead (if OOO), or Escalation Channel.

Authorized Knowledge Mesh Documentation:
${contextChunks || "General company guidelines apply."}

Critical Directives:
1. Provide a direct, highly helpful, articulate, and accurate answer to the user query.
2. Provide code snippets, command line examples, or step-by-step instructions where applicable.
3. NEVER mention "Patchamomma". Always refer to "the company", "our team", or "Company".
4. If asked about tasks, reference their actual onboarding tasks listed above.
5. If asked about timesheets, explain the Friday 5:00 PM policy and note that they can submit via the Timesheet Status action.
6. Keep formatting clean with clear markdown headings or bullet points where appropriate.
7. Point to Person Escalation: If you do not have sufficient information in the knowledge base to answer the question with complete confidence, or if the employee asks to speak to a person, connect with a human, or contact their team leads, explicitly provide the Point-to-Person contact details:
   - Assigned Onboarding Buddy: ${employee.assigned_buddy_name || "Priya Nair"} (${employee.assigned_buddy_email || "priya.nair@company.com"})
   - Direct Reporting Manager: Sarah Jenkins (sarah.j@company.com)
   - IT Systems Admin: Marcus Vance (marcus.v@company.com, #help-it)
   - People Operations (HR): Amanda Walker (amanda.w@company.com, #people-ops)
   Invite them to use the "Point of Contact" quick action in their dashboard.`;

        const response = await ai.models.generateContent({
          model: "gemini-3.6-flash",
          contents: `${systemPrompt}\n\nEmployee Query: "${message}"`,
        });

        const replyText = response.text || "";
        if (replyText.trim()) {
          const suggested: string[] = [];
          const lower = message.toLowerCase();
          if (lower.includes("task") || lower.includes("onboard")) suggested.push("View Pending Tasks");
          if (lower.includes("time") || lower.includes("hour")) suggested.push("Check Timesheet Status");
          if (lower.includes("code") || lower.includes("log") || lower.includes("git")) suggested.push("Coding Standards");
          if (lower.includes("person") || lower.includes("human") || lower.includes("contact") || lower.includes("buddy") || lower.includes("help") || lower.includes("who")) {
            suggested.push("Point of Contact");
          }
          if (suggested.length === 0) {
            suggested.push("Point of Contact", "Coding Standards", "Check Timesheet Status");
          }

          const effectiveSessionId = session_id || `sess-${employee.employee_id.toLowerCase()}`;
          // Persist turn to Cloud Firestore
          try {
            await callPythonBackend({
              action: "record_chat_turn",
              identity: employee.employee_id,
              session_id: effectiveSessionId,
              user_message: message,
              assistant_message: replyText,
              agent: "Company AI Assistant (Gemini 3.6)",
            });
          } catch (recErr: any) {
            console.warn("Firestore session persist note:", recErr.message);
          }

          res.json({
            response: replyText,
            session_id: effectiveSessionId,
            agent_invoked: "Company AI Assistant (Gemini 3.6)",
            suggested_actions: suggested,
            timestamp: new Date().toISOString(),
          });
          return;
        }
      } catch (geminiErr: any) {
        console.warn("Gemini generation fallback:", geminiErr.message);
      }
    }

    // Fallback to Python multi-agent system
    const pyResult = await callPythonBackend({
      action: "chat",
      identity: req.employee!.employee_id,
      message,
      session_id,
    });

    if (pyResult.error) {
      res.status(500).json({ detail: pyResult.error });
      return;
    }

    res.json({
      response: pyResult.response,
      session_id: pyResult.session_id,
      agent_invoked: pyResult.agent_invoked || "Supervisor Agent",
      suggested_actions: pyResult.suggested_actions || [],
      timestamp: new Date().toISOString(),
    });
  } catch (err: any) {
    res.status(500).json({ detail: err.message || "Chat agent service error" });
  }
});

// Assistant Converse Gateway (alias for /api/v1/chat)
app.post("/api/v1/assistant/converse", requireAuth, async (req: AuthenticatedRequest, res) => {
  try {
    const { message, session_id } = req.body;
    if (!message) {
      res.status(400).json({ detail: "Message is required." });
      return;
    }
    const pyResult = await callPythonBackend({
      action: "chat",
      identity: req.employee!.employee_id,
      message,
      session_id,
    });
    res.json(pyResult);
  } catch (err: any) {
    res.status(500).json({ detail: err.message || "Chat agent service error" });
  }
});

// 4. Onboarding Status
app.get("/api/v1/onboarding/my-status", requireAuth, async (req: AuthenticatedRequest, res) => {
  try {
    const pyResult = await callPythonBackend({
      action: "get_checklist",
      identity: req.employee!.employee_id,
    });
    if (pyResult && !pyResult.error) {
      res.json(pyResult);
      return;
    }
    res.status(404).json({ detail: "Onboarding checklist not found." });
  } catch (e: any) {
    res.status(500).json({ detail: e.message || "Failed to fetch checklist" });
  }
});

// 5. Complete Onboarding Task
app.post("/api/v1/onboarding/complete-task", requireAuth, async (req: AuthenticatedRequest, res) => {
  const { task_id } = req.body;
  if (!task_id) {
    res.status(400).json({ detail: "task_id is required." });
    return;
  }

  try {
    const pyResult = await callPythonBackend({
      action: "complete_task",
      identity: req.employee!.employee_id,
      task_id,
    });
    if (pyResult && pyResult.checklist) {
      res.json(pyResult.checklist);
      return;
    }
    res.status(400).json({ detail: "Task not found or already completed." });
  } catch (e: any) {
    res.status(500).json({ detail: e.message || "Failed to complete task" });
  }
});

// 6. Team Onboarding Progress (Manager / HR)
app.get("/api/v1/onboarding/team-progress", requireAuth, async (req: AuthenticatedRequest, res) => {
  try {
    const summary = await callPythonBackend({
      action: "team_progress",
      identity: req.employee!.employee_id,
    });
    res.json(summary);
  } catch (e: any) {
    res.status(500).json({ detail: e.message || "Failed to fetch team progress" });
  }
});

// 7. Knowledge Search
app.get("/api/v1/knowledge/search", requireAuth, async (req: AuthenticatedRequest, res) => {
  const query = (req.query.query as string) || "";
  try {
    const searchRes = await callPythonBackend({
      action: "search_knowledge",
      identity: req.employee!.employee_id,
      query,
    });
    res.json(searchRes);
  } catch (e: any) {
    res.status(500).json({ detail: e.message || "Failed to search knowledge base" });
  }
});

// 7b. Knowledge Mesh Insights (Recent Documentation & Policy Updates)
app.get("/api/v1/knowledge/insights", requireAuth, async (req: AuthenticatedRequest, res) => {
  try {
    const insights = await callPythonBackend({
      action: "get_insights",
      identity: req.employee!.employee_id,
    });
    res.json(insights);
  } catch (e: any) {
    res.status(500).json({ detail: e.message || "Failed to fetch insights" });
  }
});

// 7c. Persistent Session History
app.get("/api/v1/session/history", requireAuth, async (req: AuthenticatedRequest, res) => {
  const sessionId = (req.query.session_id as string) || undefined;
  try {
    const session = await callPythonBackend({
      action: "session_history",
      identity: req.employee!.employee_id,
      session_id: sessionId,
    });
    res.json(session);
  } catch (e: any) {
    res.status(500).json({ detail: e.message || "Failed to fetch session history" });
  }
});

// 8. Timesheets
app.get("/api/v1/timesheets/my-status", requireAuth, async (req: AuthenticatedRequest, res) => {
  try {
    const status = await callPythonBackend({
      action: "timesheet_status",
      identity: req.employee!.employee_id,
    });
    res.json(status);
  } catch (e: any) {
    res.status(500).json({ detail: e.message || "Failed to fetch timesheet" });
  }
});

// 8b. Submit Timesheet
app.post("/api/v1/timesheets/submit", requireAuth, async (req: AuthenticatedRequest, res) => {
  try {
    const { hours, notes } = req.body;
    const pyResult = await callPythonBackend({
      action: "submit_timesheet",
      identity: req.employee!.employee_id,
      hours: typeof hours === "number" ? hours : parseFloat(hours) || 40.0,
      notes: notes || "",
    });
    res.json(pyResult);
  } catch (err: any) {
    res.status(500).json({ detail: err.message || "Failed to submit timesheet" });
  }
});

// 8c. Knowledge Mesh Documents Catalog & Viewer
app.get("/api/v1/documents/all", requireAuth, async (req: AuthenticatedRequest, res) => {
  try {
    const pyResult = await callPythonBackend({
      action: "get_all_documents",
      identity: req.employee!.employee_id,
    });
    res.json(pyResult);
  } catch (err: any) {
    res.status(500).json({ detail: err.message || "Failed to fetch documents" });
  }
});

app.get("/api/v1/documents/:docId", requireAuth, async (req: AuthenticatedRequest, res) => {
  const { docId } = req.params;
  try {
    const doc = await callPythonBackend({
      action: "get_document",
      identity: req.employee!.employee_id,
      doc_id: docId,
    });
    if (doc && doc.error) {
      res.status(403).json(doc);
      return;
    }
    res.json(doc);
  } catch (err: any) {
    res.status(500).json({ detail: err.message || "Failed to fetch document" });
  }
});

// 8d. Point to Person Escalation & Team Directory
app.get("/api/v1/contacts/points-of-contact", requireAuth, async (req: AuthenticatedRequest, res) => {
  try {
    const contacts = await callPythonBackend({
      action: "get_points_of_contact",
      identity: req.employee!.employee_id,
    });
    res.json(contacts);
  } catch (err: any) {
    res.status(500).json({ detail: err.message || "Failed to fetch points of contact" });
  }
});

// 9. Incidents
app.post("/api/v1/incidents/create", requireAuth, async (req: AuthenticatedRequest, res) => {
  const { category, summary, severity } = req.body;
  if (!summary || summary.trim().length < 5) {
    res.status(400).json({ detail: "Summary must be at least 5 characters long." });
    return;
  }
  try {
    const inc = await callPythonBackend({
      action: "create_incident",
      identity: req.employee!.employee_id,
      category: category || "Platform / General",
      summary,
      severity: severity || "MEDIUM",
    });
    res.json(inc);
  } catch (e: any) {
    res.status(500).json({ detail: e.message || "Failed to create incident" });
  }
});

// 10. Integrations & Enterprise Cloud Sync Status (Dual-Mode Inspector)
app.get("/api/v1/integrations/status", requireAuth, async (req: AuthenticatedRequest, res) => {
  try {
    const status = await callPythonBackend({
      action: "integration_status",
      identity: req.employee!.employee_id,
    });
    res.json(status);
  } catch (e: any) {
    res.status(500).json({ detail: e.message || "Failed to check integration status" });
  }
});


// Serve frontend assets
const publicPath = path.join(process.cwd(), "public");
app.use(express.static(publicPath, { index: false }));

// Main index.html route with dynamic Client ID interpolation
app.get("*", (_req, res) => {
  const indexPath = path.join(publicPath, "index.html");
  if (fs.existsSync(indexPath)) {
    let html = fs.readFileSync(indexPath, "utf-8");
    const clientId = process.env.GOOGLE_OAUTH_CLIENT_ID || "";
    html = html.replace(/\{\{GOOGLE_CLIENT_ID\}\}/g, clientId);
    res.setHeader("Content-Type", "text/html; charset=utf-8");
    res.send(html);
  } else {
    res.status(404).send("Application static files not found");
  }
});

app.listen(PORT, "0.0.0.0", () => {
  console.log(`Onboarding Employee Assistant server running on http://0.0.0.0:${PORT}`);
});

