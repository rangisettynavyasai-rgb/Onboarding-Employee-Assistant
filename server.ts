import express, { Request, Response, NextFunction } from "express";
import cors from "cors";
import path from "path";
import fs from "fs";
import { AuthService, OnboardingService, OperationsService, KnowledgeService, ProactiveService, SessionService } from "./src/services.js";
import { SupervisorAgent } from "./src/agents.js";
import { EmployeeRecord, IncidentSeverity } from "./src/types.js";
import { callPythonBackend } from "./src/pythonBridge.js";

const app = express();
const PORT = 3000;

app.use(cors());
app.use(express.json());

// Extend express Request to hold authenticated employee
interface AuthenticatedRequest extends Request {
  employee?: EmployeeRecord;
}

// Authentication Middleware
function requireAuth(req: AuthenticatedRequest, res: Response, next: NextFunction) {
  const authHeader = req.headers.authorization;
  if (!authHeader) {
    res.status(401).json({ detail: "Missing Authorization Bearer header." });
    return;
  }

  const employee = AuthService.resolveEmployee(authHeader);
  if (!employee) {
    res.status(401).json({ detail: "Invalid or expired Google Identity token." });
    return;
  }

  req.employee = employee;
  next();
}

// 1. Health Check
app.get("/health", (_req, res) => {
  res.json({
    status: "ok",
    service: "Onboarding-Employee-Assistant",
    runtime: "Node.js 22 LTS",
    timestamp: new Date().toISOString(),
  });
});

// 1b. Direct Employee Sign-In (Corporate Directory & SSO)
app.post("/api/v1/auth/login", (req, res) => {
  const { identity } = req.body;
  if (!identity || typeof identity !== "string") {
    res.status(400).json({ detail: "Email or Employee ID is required." });
    return;
  }

  const employee = AuthService.resolveEmployee(identity);
  if (!employee) {
    res.status(401).json({ detail: "Invalid employee credentials or identity not found." });
    return;
  }

  res.json({
    status: "authenticated",
    token: identity,
    employee: {
      employee_id: employee.employee_id,
      name: employee.name,
      email: employee.email,
      team: employee.team,
      department: employee.department,
      job_role: employee.job_role,
      authorization_role: employee.authorization_role,
      is_day_one: employee.is_day_one,
    },
  });
});

// 2. Proactive Landing Screen
app.post("/api/v1/landing", requireAuth, (req: AuthenticatedRequest, res) => {
  const landing = ProactiveService.generateLanding(req.employee!);
  res.json(landing);
});

// 3. Conversational Multi-Agent Hub
app.post("/api/v1/chat", requireAuth, async (req: AuthenticatedRequest, res) => {
  try {
    const { message, session_id } = req.body;
    if (!message || typeof message !== "string") {
      res.status(400).json({ detail: "Message is required." });
      return;
    }

    const session = await SessionService.getOrCreateSession(req.employee!.employee_id, session_id);
    session.history.push({ role: "user", content: message, timestamp: new Date().toISOString() });

    let responseText = "";
    let agentInvoked = "Supervisor Agent";
    let suggestedActions = ["Coding Standards", "View Pending Tasks"];

    try {
      const pyResult = await callPythonBackend({
        action: "chat",
        identity: req.employee!.employee_id,
        message,
      });
      if (pyResult && pyResult.response) {
        responseText = pyResult.response;
        agentInvoked = pyResult.agent_invoked || "Python Supervisor Agent";
        if (pyResult.suggested_actions) {
          suggestedActions = pyResult.suggested_actions;
        }
      }
    } catch (pyErr) {
      console.warn("Python backend chat failed, falling back to TS:", pyErr);
    }

    if (!responseText) {
      const result = await SupervisorAgent.orchestrate(req.employee!, message);
      responseText = result.response;
      agentInvoked = result.agent_invoked;
      suggestedActions = result.suggested_actions;
    }

    session.history.push({ role: "assistant", content: responseText, timestamp: new Date().toISOString() });
    await SessionService.saveSession(session);

    res.json({
      response: responseText,
      session_id: session.session_id,
      agent_invoked: agentInvoked,
      suggested_actions: suggestedActions,
      timestamp: new Date().toISOString(),
    });
  } catch (err: any) {
    res.status(500).json({ detail: err.message || "Internal server error" });
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
    const session = await SessionService.getOrCreateSession(req.employee!.employee_id, session_id);
    session.history.push({ role: "user", content: message, timestamp: new Date().toISOString() });

    const result = await SupervisorAgent.orchestrate(req.employee!, message);
    session.history.push({ role: "assistant", content: result.response, timestamp: new Date().toISOString() });
    await SessionService.saveSession(session);

    res.json({
      response: result.response,
      session_id: session.session_id,
      agent_invoked: result.agent_invoked,
      suggested_actions: result.suggested_actions,
      timestamp: new Date().toISOString(),
    });
  } catch (err: any) {
    res.status(500).json({ detail: err.message || "Internal server error" });
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
  } catch (e) {
    console.warn("Python backend error for checklist, falling back to TS:", e);
  }

  // Fallback to TS
  const checklist = OnboardingService.getChecklist(req.employee!.employee_id);
  if (!checklist) {
    res.status(404).json({ detail: "Onboarding checklist not found." });
    return;
  }
  res.json(checklist);
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
  } catch (e) {
    console.warn("Python backend error for complete_task:", e);
  }

  const success = OnboardingService.completeTask(req.employee!.employee_id, task_id);
  if (!success) {
    res.status(400).json({ detail: "Task not found or already completed." });
    return;
  }
  const updated = OnboardingService.getChecklist(req.employee!.employee_id);
  res.json(updated);
});

// 6. Team Onboarding Progress (Manager / HR)
app.get("/api/v1/onboarding/team-progress", requireAuth, (req: AuthenticatedRequest, res) => {
  const summary = OnboardingService.getTeamProgress(req.employee!);
  res.json(summary);
});

// 7. Knowledge Search
app.get("/api/v1/knowledge/search", requireAuth, (req: AuthenticatedRequest, res) => {
  const query = (req.query.query as string) || "";
  const chunks = KnowledgeService.searchAuthorized(req.employee!, query);
  res.json({
    query,
    count: chunks.length,
    chunks,
  });
});

// 7b. Knowledge Mesh Insights (Recent Documentation & Policy Updates)
app.get("/api/v1/knowledge/insights", requireAuth, (req: AuthenticatedRequest, res) => {
  const insights = KnowledgeService.getAuthorizedInsights(req.employee!);
  res.json({
    employee_id: req.employee!.employee_id,
    team: req.employee!.team,
    clearance: req.employee!.authorization_role,
    total_insights: insights.length,
    insights,
    timestamp: new Date().toISOString(),
  });
});

// 7c. Persistent Session History (Firestore Backed)
app.get("/api/v1/session/history", requireAuth, async (req: AuthenticatedRequest, res) => {
  const sessionId = (req.query.session_id as string) || undefined;
  const session = await SessionService.getOrCreateSession(req.employee!.employee_id, sessionId);
  res.json({
    session_id: session.session_id,
    employee_id: session.employee_id,
    created_at: session.created_at,
    last_accessed_at: session.last_accessed_at,
    message_count: session.history.length,
    history: session.history,
  });
});


// 8. Timesheets
app.get("/api/v1/timesheets/my-status", requireAuth, (req: AuthenticatedRequest, res) => {
  const status = OperationsService.getTimesheetStatus(req.employee!.employee_id);
  res.json(status);
});

// 9. Incidents
app.post("/api/v1/incidents/create", requireAuth, (req: AuthenticatedRequest, res) => {
  const { category, summary, severity } = req.body;
  if (!summary || summary.trim().length < 5) {
    res.status(400).json({ detail: "Summary must be at least 5 characters long." });
    return;
  }
  const inc = OperationsService.createIncident(
    req.employee!,
    category || "Platform / General",
    summary,
    (severity as IncidentSeverity) || IncidentSeverity.MEDIUM
  );
  res.json(inc);
});

// Serve frontend assets
const publicPath = path.join(process.cwd(), "public");
app.use(express.static(publicPath));

// Main index.html route with dynamic Client ID interpolation
app.get("*", (_req, res) => {
  const indexPath = path.join(publicPath, "index.html");
  if (fs.existsSync(indexPath)) {
    let html = fs.readFileSync(indexPath, "utf-8");
    const clientId = process.env.GOOGLE_OAUTH_CLIENT_ID || "";
    html = html.replace("__GOOGLE_CLIENT_ID__", clientId);
    res.setHeader("Content-Type", "text/html; charset=utf-8");
    res.send(html);
  } else {
    res.status(404).send("Application static files not found");
  }
});

app.listen(PORT, "0.0.0.0", () => {
  console.log(`Onboarding Employee Assistant server running on http://0.0.0.0:${PORT}`);
});
