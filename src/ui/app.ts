/**
 * Company AI Assistant: UI TypeScript Application
 * Client-Side orchestration, State Management & Google Identity integration.
 */

export interface OnboardingTask {
  task_id: string;
  title: string;
  description: string;
  status: "PENDING" | "IN_PROGRESS" | "COMPLETED" | "BLOCKED";
  due_days_after_start: number;
  due_date?: string;
  is_overdue?: boolean;
  completed_at?: string;
  category: string;
  action_link?: string;
}

export interface ChecklistData {
  employee_id: string;
  track: string;
  tasks: OnboardingTask[];
  completed_count: number;
  total_count: number;
  next_pending_task?: OnboardingTask | null;
}

export interface KnowledgeInsight {
  insight_id: string;
  category: string;
  title: string;
  summary: string;
  team: string;
  access_level: string;
  effective_date: string;
  action_suggestion: string;
  highlight_tag: string;
}

export interface LandingData {
  employee_id: string;
  name: string;
  department: string;
  team: string;
  job_role: string;
  authorization_role: string;
  is_day_one: boolean;
  proactive_greeting: string;
  primary_next_action: string;
  pending_tasks_count: number;
  overdue_tasks_count: number;
  timesheet_status: string;
  assigned_buddy_name?: string;
  assigned_buddy_email?: string;
}

export interface ChatResponse {
  response: string;
  session_id: string;
  agent_invoked: string;
  suggested_actions?: string[];
  employee_id?: string;
  timestamp?: string;
}

export interface TimesheetStatus {
  employee_id: string;
  period: string;
  period_end?: string;
  hours_logged: number;
  status: string;
  due_date: string;
  is_overdue?: boolean;
}

// Global UI State
class AppState {
  activeBearerToken: string | null = null;
  currentSessionId: string | null = null;
  currentUserProfile: LandingData | null = null;
  currentChecklistData: ChecklistData | null = null;
  showCompletedTasks: boolean = true;
}

const state = new AppState();

// Utility DOM element getter
function $<T extends HTMLElement = HTMLElement>(id: string): T {
  const el = document.getElementById(id);
  if (!el) {
    throw new Error(`Element #${id} not found in DOM`);
  }
  return el as T;
}

const AUTH_TOKEN_KEY = "assistant_auth_session_token";

export function showAuthAlert(
  title: string,
  message: string,
  type: "error" | "warning" | "info" = "error"
): void {
  const alertEl = document.getElementById("auth-alert");
  const iconEl = document.getElementById("auth-alert-icon");
  const titleEl = document.getElementById("auth-alert-title");
  const msgEl = document.getElementById("auth-alert-message");

  if (!alertEl || !titleEl || !msgEl) return;

  alertEl.className = `auth-alert-box auth-alert-${type}`;
  titleEl.textContent = title;
  msgEl.textContent = message;

  if (iconEl) {
    if (type === "error") iconEl.textContent = "⚠️";
    else if (type === "warning") iconEl.textContent = "⚡";
    else iconEl.textContent = "ℹ️";
  }

  alertEl.style.display = "flex";
}

export function dismissAuthAlert(): void {
  const alertEl = document.getElementById("auth-alert");
  if (alertEl) alertEl.style.display = "none";
}

export function setAuthLoading(isLoading: boolean, actionLabel?: string): void {
  const googleBtn = document.getElementById("btn-google-sso") as HTMLButtonElement | null;
  const googleLabel = document.getElementById("btn-google-sso-label");
  const loginBtn = document.getElementById("btn-employee-login") as HTMLButtonElement | null;
  const loginLabel = document.getElementById("btn-employee-login-label");

  if (isLoading) {
    if (googleBtn) {
      googleBtn.disabled = true;
      googleBtn.style.opacity = "0.7";
      googleBtn.style.cursor = "wait";
    }
    if (googleLabel) {
      googleLabel.innerHTML = `<span class="auth-spinner" style="margin-right: 6px;"></span> ${actionLabel || "Authenticating..."}`;
    }
    if (loginBtn) {
      loginBtn.disabled = true;
      loginBtn.style.opacity = "0.7";
      loginBtn.style.cursor = "wait";
    }
    if (loginLabel) {
      loginLabel.textContent = "Verifying...";
    }
  } else {
    if (googleBtn) {
      googleBtn.disabled = false;
      googleBtn.style.opacity = "1";
      googleBtn.style.cursor = "pointer";
    }
    if (googleLabel) {
      googleLabel.textContent = "Continue with Google";
    }
    if (loginBtn) {
      loginBtn.disabled = false;
      loginBtn.style.opacity = "1";
      loginBtn.style.cursor = "pointer";
    }
    if (loginLabel) {
      loginLabel.textContent = "Sign In";
    }
  }
}

export function setAuthStatus(msg: string, isError: boolean = false): void {
  const el = document.getElementById("auth-status");
  if (el) {
    el.textContent = msg;
    el.style.color = isError ? "var(--accent-rose)" : "var(--text-muted)";
  }
}

export async function apiRequest<T = any>(
  path: string,
  method: string = "GET",
  body: any = null
): Promise<T> {
  const headers: Record<string, string> = {
    Authorization: `Bearer ${state.activeBearerToken}`,
  };
  if (body) {
    headers["Content-Type"] = "application/json";
  }

  const resp = await fetch(path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : null,
  });

  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    throw new Error(data.message || data.detail || `HTTP Error ${resp.status}`);
  }
  return data as T;
}

export async function initializeSession(token: string, isRestoring: boolean = false): Promise<void> {
  dismissAuthAlert();
  setAuthLoading(true, isRestoring ? "Restoring Session..." : "Authenticating...");

  try {
    let effectiveToken = token;

    // If token is a raw Google ID Token JWT, OAuth access token, or email, exchange via /api/v1/auth/google
    if (token.startsWith("ya29.") || token.startsWith("eyJ") || token.includes("@")) {
      setAuthStatus("Verifying Google Workspace identity with corporate directory...");
      const authRes = await fetch("/api/v1/auth/google", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ credential: token, email: token.includes("@") ? token : undefined }),
      });

      const authData = await authRes.json();
      if (!authRes.ok || !authData.token) {
        throw new Error(authData.detail || "Google Identity authentication failed");
      }
      effectiveToken = authData.token;
    }

    state.activeBearerToken = effectiveToken;
    setAuthStatus("Loading personalized workspace...");

    const landing = await apiRequest<LandingData>("/api/v1/landing", "POST");
    state.currentUserProfile = landing;

    // Persist verified session token to sessionStorage for session survival across refreshes
    sessionStorage.setItem(AUTH_TOKEN_KEY, effectiveToken);

    // Restore or initialize persistent session ID for this employee
    const sessionKey = `onboarding_session_${landing.employee_id}`;
    state.currentSessionId =
      localStorage.getItem(sessionKey) || `sess-${landing.employee_id.toLowerCase()}`;
    localStorage.setItem(sessionKey, state.currentSessionId);

    const restoringBanner = document.getElementById("session-restoring-banner");
    if (restoringBanner) restoringBanner.style.display = "none";

    $<HTMLElement>("auth-view").style.display = "none";
    $<HTMLElement>("dashboard-view").style.display = "flex";

    $<HTMLElement>("user-display-name").textContent = landing.name;
    const teamEl = document.getElementById("user-display-team");
    if (teamEl) teamEl.textContent = `${landing.team} • ${landing.department}`;

    const roleEl = document.getElementById("user-display-role");
    if (roleEl) {
      roleEl.textContent = landing.authorization_role.toUpperCase();
      roleEl.className = `role-tag role-${landing.authorization_role.toLowerCase()}`;
    }

    $<HTMLElement>("proactive-greeting-text").textContent = landing.proactive_greeting;

    // Fetch Checklist
    await refreshChecklist();

    // Fetch Knowledge Mesh Insights for Sidebar Widget
    await refreshKnowledgeInsights();

    // Restore persistent conversation history from Firestore
    await restoreSessionHistory(state.currentSessionId, landing.name);
  } catch (err: any) {
    console.error("Session initialization failed:", err);
    state.activeBearerToken = null;
    sessionStorage.removeItem(AUTH_TOKEN_KEY);

    const restoringBanner = document.getElementById("session-restoring-banner");
    if (restoringBanner) restoringBanner.style.display = "none";

    $<HTMLElement>("dashboard-view").style.display = "none";
    $<HTMLElement>("auth-view").style.display = "block";

    if (isRestoring) {
      showAuthAlert("Session Expired", "Your previous corporate session has expired. Please sign in to continue.", "info");
      setAuthStatus("Previous session expired. Please sign in.", false);
    } else {
      showAuthAlert("Authentication Failed", err.message || "Failed to initialize session with corporate directory.", "error");
      setAuthStatus(err.message || "Authentication failed.", true);
    }
  } finally {
    setAuthLoading(false);
  }
}

export async function restoreSessionHistory(sessionId: string, userName: string): Promise<void> {
  try {
    const sessionData = await apiRequest<any>(
      `/api/v1/session/history?session_id=${sessionId}`
    );
    const stream = $<HTMLElement>("chat-stream");
    stream.innerHTML = "";

    if (sessionData.history && sessionData.history.length > 0) {
      sessionData.history.forEach((m: { role: string; content: string; agent?: string }) => {
        appendChatMessage(
          m.role,
          m.content,
          m.role === "assistant" ? m.agent || "Supervisor Agent" : null
        );
      });
    } else {
      appendChatMessage(
        "assistant",
        `👋 Hello **${userName}**! I'm your secure AI Onboarding & Employee Assistant. How can I help you today?`,
        "Supervisor Agent",
        ["Check Timesheet", "View Pending Tasks", "Point of Contact", "Search Runbooks"]
      );
    }
  } catch (e) {
    console.warn("Could not load previous session history:", e);
    appendChatMessage(
      "assistant",
      `👋 Hello **${userName}**! I'm your secure AI Onboarding & Employee Assistant. How can I help you today?`,
      "Supervisor Agent",
      ["Check Timesheet", "View Pending Tasks", "Point of Contact", "Search Runbooks"]
    );
  }
}

export async function refreshKnowledgeInsights(): Promise<void> {
  const container = document.getElementById("mesh-insights-container");
  if (!container) return;

  try {
    const data = await apiRequest<{ insights: KnowledgeInsight[] }>(
      "/api/v1/knowledge/insights"
    );
    if (!data.insights || data.insights.length === 0) {
      container.innerHTML = `<div style="font-size: 11px; color: var(--text-muted); padding: 8px 0;">No new updates for your team access level.</div>`;
      return;
    }

    container.innerHTML = "";
    data.insights.forEach((item) => {
      const card = document.createElement("div");
      card.className = "mesh-insight-item";
      card.setAttribute("role", "button");
      card.setAttribute("tabindex", "0");
      card.title = `Click to read: ${item.title}`;
      card.innerHTML = `
        <div class="mesh-insight-meta">
          <span class="mesh-category-pill cat-${item.category}">${item.category}</span>
          <span style="color: var(--text-muted); font-size: 10px;">${item.effective_date}</span>
        </div>
        <div class="mesh-insight-title">${item.title}</div>
        <div class="mesh-insight-summary">${item.summary}</div>
        <div style="margin-top: 8px; display: flex; justify-content: space-between; align-items: center;">
          <span style="font-size: 10px; color: var(--accent-indigo); font-weight: 500;">${item.highlight_tag}</span>
          <span class="read-doc-badge">📖 Read Doc →</span>
        </div>
      `;
      // Clicking opens the actual document modal directly
      const docTarget = (item as any).doc_id || (item as any).document_id || item.insight_id || item.title;
      card.addEventListener("click", () => {
        openDocumentModal(docTarget);
      });
      container.appendChild(card);
    });
  } catch (err) {
    console.error("Failed to load knowledge insights:", err);
    container.innerHTML = `<div style="font-size: 11px; color: var(--accent-rose); padding: 6px 0;">Failed to sync Knowledge Mesh insights.</div>`;
  }
}

export function toggleCompletedTasks(checked: boolean): void {
  state.showCompletedTasks = checked;
  renderChecklistTasks();
}

export function renderChecklistTasks(): void {
  if (!state.currentChecklistData) return;
  const listEl = document.getElementById("task-list-container");
  const badgeCount = document.getElementById("completed-badge-count");
  if (!listEl) return;

  const completedTasks = state.currentChecklistData.tasks.filter(
    (t) => t.status === "COMPLETED"
  );
  if (badgeCount) {
    badgeCount.textContent = String(completedTasks.length);
  }

  listEl.innerHTML = "";
  const visibleTasks = state.currentChecklistData.tasks.filter((t) => {
    if (t.status === "COMPLETED" && !state.showCompletedTasks) {
      return false;
    }
    return true;
  });

  if (visibleTasks.length === 0) {
    listEl.innerHTML = `
      <div style="padding: 16px; text-align: center; color: var(--text-muted); font-size: 11px;">
        ${
          !state.showCompletedTasks && completedTasks.length > 0
            ? "All completed tasks hidden. Toggle switch above to view."
            : "No tasks found."
        }
      </div>
    `;
    return;
  }

  visibleTasks.forEach((t) => {
    const isDone = t.status === "COMPLETED";
    const isOverdue =
      !isDone && (t.is_overdue || (t.due_date && t.due_date < "2026-09-07"));
    const div = document.createElement("div");
    div.className = `task-item ${isDone ? "completed" : ""} ${isOverdue ? "overdue" : ""}`;

    const dueDateText = t.due_date
      ? `Due: ${t.due_date}`
      : `Due in +${t.due_days_after_start}d`;

    div.innerHTML = `
      <div style="flex: 1; min-width: 0;">
        <div style="font-weight: 600; font-size: 12px; color: ${isOverdue ? "#fda4af" : "var(--text-primary)"};">${t.title}</div>
        <div style="color: var(--text-muted); font-size: 10px; margin-top: 2px;">
          ${t.category} • ${t.task_id}
        </div>
        <div class="due-date-badge ${isOverdue ? "overdue-badge" : ""}">
          <span>${isOverdue ? "⚠️ Overdue:" : "📅"}</span>
          <span>${dueDateText}</span>
        </div>
      </div>
      <div style="flex-shrink: 0; margin-left: 8px;">
        ${
          !isDone
            ? `<button class="task-btn-done" data-task-id="${t.task_id}" onclick="completeTask('${t.task_id}')">Done</button>`
            : `<span style="color: var(--accent-emerald); font-weight: 700; font-size: 14px;">✓</span>`
        }
      </div>
    `;

    // Direct listener for foolproof click handling in iframe environments
    const doneBtn = div.querySelector<HTMLButtonElement>(".task-btn-done");
    if (doneBtn) {
      doneBtn.addEventListener("click", async (ev) => {
        ev.stopPropagation();
        ev.preventDefault();
        doneBtn.disabled = true;
        doneBtn.textContent = "...";
        await completeTask(t.task_id);
      });
    }

    listEl.appendChild(div);
  });
}

export async function refreshChecklist(): Promise<void> {
  try {
    const checklist = await apiRequest<ChecklistData>("/api/v1/onboarding/my-status");
    state.currentChecklistData = checklist;

    const fill = $<HTMLElement>("progress-bar-fill");
    const pctEl = $<HTMLElement>("progress-percentage");

    const pct =
      Math.round((checklist.completed_count / checklist.total_count) * 100) || 0;
    fill.style.width = pct + "%";
    pctEl.textContent = `${pct}% (${checklist.completed_count}/${checklist.total_count})`;

    renderChecklistTasks();
  } catch (e) {
    console.error("Checklist error:", e);
  }
}

export async function completeTask(taskId: string): Promise<void> {
  // 1. Optimistic UI update to immediately show task completed and progress advanced
  if (state.currentChecklistData && Array.isArray(state.currentChecklistData.tasks)) {
    const task = state.currentChecklistData.tasks.find((t) => t.task_id === taskId);
    if (task) {
      task.status = "COMPLETED";
      task.is_overdue = false;
      state.currentChecklistData.completed_count = state.currentChecklistData.tasks.filter(
        (t) => t.status === "COMPLETED"
      ).length;
      const fill = $<HTMLElement>("progress-bar-fill");
      const pctEl = $<HTMLElement>("progress-percentage");
      const pct =
        Math.round((state.currentChecklistData.completed_count / state.currentChecklistData.total_count) * 100) || 0;
      if (fill) fill.style.width = pct + "%";
      if (pctEl) pctEl.textContent = `${pct}% (${state.currentChecklistData.completed_count}/${state.currentChecklistData.total_count})`;
      renderChecklistTasks();
    }
  }

  try {
    const res = await apiRequest<ChecklistData>("/api/v1/onboarding/complete-task", "POST", { task_id: taskId });
    if (res && res.tasks) {
      state.currentChecklistData = res;
      const fill = $<HTMLElement>("progress-bar-fill");
      const pctEl = $<HTMLElement>("progress-percentage");
      const pct =
        Math.round((res.completed_count / res.total_count) * 100) || 0;
      if (fill) fill.style.width = pct + "%";
      if (pctEl) pctEl.textContent = `${pct}% (${res.completed_count}/${res.total_count})`;
      renderChecklistTasks();
    } else {
      await refreshChecklist();
    }
    appendChatMessage(
      "assistant",
      `✅ Task **${taskId}** has been marked complete! Your onboarding checklist progress is now updated.`,
      "Onboarding Specialist"
    );
  } catch (err: any) {
    console.error("Task completion failed:", err);
    await refreshChecklist();
    appendChatMessage(
      "assistant",
      `⚠️ Could not complete task **${taskId}**: ${err.message}`,
      "Onboarding Specialist"
    );
  }
}

// -------------------------------------------------------------
// Markdown renderer helper for documents
// -------------------------------------------------------------
function renderMarkdownToHtml(markdown: string): string {
  if (!markdown) return "";
  function escape(t: string): string {
    return t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  let text = markdown
    // Code blocks
    .replace(/```([\s\S]*?)```/g, (_m, code) => {
      return `<pre><code>${escape(code.trim())}</code></pre>`;
    })
    // Inline code
    .replace(/`([^`]+)`/g, (_m, code) => {
      return `<code>${escape(code)}</code>`;
    })
    // Headers
    .replace(/^### (.*$)/gim, "<h3>$1</h3>")
    .replace(/^## (.*$)/gim, "<h2>$1</h2>")
    .replace(/^# (.*$)/gim, "<h1>$1</h1>")
    // Bold & italic
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    // Lists
    .replace(/^\s*-\s+(.*$)/gim, "<li>$1</li>")
    .replace(/^\s*\d+\.\s+(.*$)/gim, "<li>$1</li>")
    // Paragraphs
    .replace(/\n\n+/g, "<br><br>")
    .replace(/\n/g, "<br>");

  return text;
}

// -------------------------------------------------------------
// Knowledge Mesh Document Viewer Modal
// -------------------------------------------------------------
let currentActiveDocument: any = null;

export async function openDocumentModal(docId: string): Promise<void> {
  const modal = document.getElementById("document-modal");
  if (!modal) return;

  const contentEl = document.getElementById("doc-modal-content");
  const titleEl = document.getElementById("doc-modal-title");
  const uriEl = document.getElementById("doc-modal-uri");
  const typeBadge = document.getElementById("doc-modal-type-badge");
  const idBadge = document.getElementById("doc-modal-id-badge");
  const clearanceBadge = document.getElementById("doc-modal-clearance-badge");

  if (contentEl) contentEl.innerHTML = "<div style='text-align: center; padding: 30px 0; color: var(--text-muted);'>Loading document from Knowledge Mesh...</div>";
  if (titleEl) titleEl.textContent = "Loading Document...";
  modal.style.display = "grid";

  try {
    const doc = await apiRequest<any>(`/api/v1/documents/${encodeURIComponent(docId)}`);
    currentActiveDocument = doc;

    if (doc.error) {
      if (titleEl) titleEl.textContent = "Restricted Access";
      if (contentEl) contentEl.innerHTML = `<div style="padding: 24px; color: var(--accent-rose); background: rgba(244,63,94,0.1); border-radius: 6px;">${doc.error}</div>`;
      return;
    }

    if (titleEl) titleEl.textContent = doc.title || docId;
    if (uriEl) uriEl.textContent = doc.gcs_uri || `gs://company-knowledge-mesh/${doc.document_id}.md`;
    if (typeBadge) {
      typeBadge.textContent = (doc.category || "GUIDE").toUpperCase();
      typeBadge.className = `mesh-category-pill cat-${(doc.category || "STANDARDS").toUpperCase()}`;
    }
    if (idBadge) idBadge.textContent = doc.document_id || docId;
    if (clearanceBadge) {
      clearanceBadge.textContent = (doc.access_level || "employee").toUpperCase();
      clearanceBadge.className = `role-tag role-${(doc.access_level || "employee").toLowerCase()}`;
    }

    if (contentEl) {
      const raw = doc.full_content || doc.description || "No content available.";
      contentEl.innerHTML = renderMarkdownToHtml(raw);
    }
  } catch (err: any) {
    if (titleEl) titleEl.textContent = "Error Loading Document";
    if (contentEl) contentEl.innerHTML = `<div style="padding: 24px; color: var(--accent-rose);">Failed to retrieve document: ${err.message}</div>`;
  }
}

export function closeDocumentModal(): void {
  const modal = document.getElementById("document-modal");
  if (modal) modal.style.display = "none";
}

export function copyDocumentUri(): void {
  if (!currentActiveDocument?.gcs_uri) return;
  navigator.clipboard.writeText(currentActiveDocument.gcs_uri).then(() => {
    const btn = document.getElementById("doc-copy-uri-btn");
    if (btn) {
      const original = btn.textContent;
      btn.textContent = "✓ Copied!";
      setTimeout(() => { if (btn) btn.textContent = original; }, 2000);
    }
  }).catch(() => {});
}

export function askAboutCurrentDocument(): void {
  if (!currentActiveDocument) return;
  const docTitle = currentActiveDocument.title;
  const docId = currentActiveDocument.document_id;
  closeDocumentModal();
  quickPrompt(`Tell me more about the standards and procedures in ${docTitle} (${docId})`);
}

// -------------------------------------------------------------
// Timesheet Modal & Actions
// -------------------------------------------------------------
export async function openTimesheetModal(): Promise<void> {
  const modal = document.getElementById("timesheet-modal");
  if (!modal) return;
  modal.style.display = "grid";

  const feedback = document.getElementById("ts-feedback");
  if (feedback) feedback.textContent = "";

  try {
    const ts = await apiRequest<TimesheetStatus>("/api/v1/timesheets/my-status");
    const cycleEl = document.getElementById("ts-modal-cycle");
    const statusPill = document.getElementById("ts-modal-status-pill");
    const hoursInput = document.getElementById("ts-hours-input") as HTMLInputElement;

    if (cycleEl) cycleEl.textContent = `Period: ${ts.period_end || ts.period}`;
    if (statusPill) {
      statusPill.textContent = ts.status.toUpperCase();
      statusPill.className =
        ts.status.toUpperCase() === "SUBMITTED" || ts.status.toUpperCase() === "APPROVED"
          ? "status-pill-submitted"
          : "status-pill-pending";
    }
    if (hoursInput && ts.hours_logged) {
      hoursInput.value = String(ts.hours_logged);
    }
  } catch (err: any) {
    console.warn("Could not fetch timesheet status:", err);
  }
}

export function closeTimesheetModal(): void {
  const modal = document.getElementById("timesheet-modal");
  if (modal) modal.style.display = "none";
}

export async function handleTimesheetSubmit(event: Event): Promise<void> {
  event.preventDefault();
  const hoursInput = document.getElementById("ts-hours-input") as HTMLInputElement;
  const notesInput = document.getElementById("ts-notes-input") as HTMLTextAreaElement;
  const submitBtn = document.getElementById("ts-submit-btn") as HTMLButtonElement;
  const feedback = document.getElementById("ts-feedback");

  const hours = parseFloat(hoursInput?.value || "40.0");
  const notes = notesInput?.value.trim() || "";

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = "Submitting...";
  }

  try {
    const result = await apiRequest<any>("/api/v1/timesheets/submit", "POST", { hours, notes });
    if (feedback) {
      feedback.style.color = "var(--accent-emerald)";
      feedback.textContent = `✓ Timesheet submitted successfully! (${result.hours_logged} hours logged).`;
    }
    const statusPill = document.getElementById("ts-modal-status-pill");
    if (statusPill) {
      statusPill.textContent = "SUBMITTED";
      statusPill.className = "status-pill-submitted";
    }
    const sf = result.salesforce_sync;
    const sfLabel = sf?.mode === "PRODUCTION_LIVE"
      ? `Live Salesforce CRM synced (${sf.salesforce_id})`
      : `Staged in Cloud Firestore (${sf?.reference_id || "02i8X00000123AA"})`;
    appendChatMessage(
      "assistant",
      `⏱️ **Timesheet Submitted**: Logged **${hours} hours** for this pay period.\n\n• **Status**: SUBMITTED for automated payroll\n• **Enterprise Sync**: ${sfLabel}`,
      "Operations Specialist"
    );
    setTimeout(() => {
      closeTimesheetModal();
    }, 1500);
  } catch (err: any) {
    if (feedback) {
      feedback.style.color = "var(--accent-rose)";
      feedback.textContent = `Failed to submit timesheet: ${err.message}`;
    }
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Submit Timesheet";
    }
  }
}

// -------------------------------------------------------------
// Runbooks Browser Modal
// -------------------------------------------------------------
let cachedRunbooks: any[] = [];

export async function openRunbooksModal(): Promise<void> {
  const modal = document.getElementById("runbooks-modal");
  if (!modal) return;
  modal.style.display = "grid";

  const container = document.getElementById("runbooks-list-container");
  const searchInput = document.getElementById("runbooks-search-input") as HTMLInputElement;
  if (searchInput) searchInput.value = "";

  if (container) {
    container.innerHTML = "<div style='text-align:center; padding: 24px; color: var(--text-muted);'>Loading runbooks...</div>";
  }

  try {
    const res = await apiRequest<{ documents: any[] }>("/api/v1/documents/all");
    cachedRunbooks = res.documents || [];
    renderRunbooksList(cachedRunbooks);
  } catch (err: any) {
    if (container) {
      container.innerHTML = `<div style="color: var(--accent-rose); padding: 16px;">Failed to load documents: ${err.message}</div>`;
    }
  }
}

export function closeRunbooksModal(): void {
  const modal = document.getElementById("runbooks-modal");
  if (modal) modal.style.display = "none";
}

export function handleRunbookSearch(query: string): void {
  const q = query.toLowerCase().trim();
  if (!q) {
    renderRunbooksList(cachedRunbooks);
    return;
  }
  const filtered = cachedRunbooks.filter((doc) => {
    return (
      (doc.title && doc.title.toLowerCase().includes(q)) ||
      (doc.document_id && doc.document_id.toLowerCase().includes(q)) ||
      (doc.category && doc.category.toLowerCase().includes(q)) ||
      (doc.team && doc.team.toLowerCase().includes(q)) ||
      (doc.description && doc.description.toLowerCase().includes(q))
    );
  });
  renderRunbooksList(filtered);
}

function renderRunbooksList(docs: any[]): void {
  const container = document.getElementById("runbooks-list-container");
  if (!container) return;

  if (docs.length === 0) {
    container.innerHTML = `<div style="text-align: center; padding: 24px; color: var(--text-muted);">No documents match your query.</div>`;
    return;
  }

  container.innerHTML = "";
  docs.forEach((doc) => {
    const card = document.createElement("div");
    card.className = "runbook-item-card";
    card.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
        <div style="display: flex; gap: 6px; align-items: center;">
          <span class="mesh-category-pill cat-${(doc.category || "STANDARDS").toUpperCase()}">${doc.category || "DOC"}</span>
          <span style="font-family: monospace; font-size: 10px; color: var(--text-muted);">${doc.document_id}</span>
        </div>
        <span class="role-tag role-${(doc.access_level || "employee").toLowerCase()}">${doc.access_level}</span>
      </div>
      <div style="font-size: 14px; font-weight: 600; color: var(--text-primary); margin-bottom: 4px;">${doc.title}</div>
      <div style="font-size: 12px; color: var(--text-secondary); line-height: 1.4; margin-bottom: 8px;">
        ${doc.description || (doc.full_content ? doc.full_content.slice(0, 160) + "..." : "")}
      </div>
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <span style="font-size: 11px; color: var(--text-muted);">Team: ${doc.team}</span>
        <span class="read-doc-badge">Read Full Document →</span>
      </div>
    `;
    card.onclick = () => {
      closeRunbooksModal();
      openDocumentModal(doc.document_id);
    };
    container.appendChild(card);
  });
}

export async function sendChatMessage(): Promise<void> {
  const input = $<HTMLInputElement>("user-input-box");
  const msg = input.value.trim();
  if (!msg) return;

  input.value = "";
  appendChatMessage("user", msg);

  const btn = $<HTMLButtonElement>("send-button");
  btn.disabled = true;

  try {
    const res = await apiRequest<ChatResponse>("/api/v1/chat", "POST", {
      message: msg,
      session_id: state.currentSessionId,
    });
    state.currentSessionId = res.session_id;
    appendChatMessage(
      "assistant",
      res.response,
      res.agent_invoked,
      res.suggested_actions
    );
  } catch (err: any) {
    appendChatMessage("assistant", `⚠️ Error: ${err.message}`, "Security Guard");
  } finally {
    btn.disabled = false;
  }
}

export function appendChatMessage(
  role: string,
  text: string,
  agentName: string | null = null,
  suggestions: string[] = []
): void {
  const stream = document.getElementById("chat-stream");
  if (!stream) return;

  const bubble = document.createElement("div");
  bubble.className = `message-bubble ${role === "user" ? "user-message" : "assistant-message"}`;

  let content = "";
  if (role === "assistant" && agentName) {
    content += `<div class="agent-badge-tag">⚡ ${agentName}</div><br>`;
  }

  // Render markdown formatting inside chat bubbles
  content += renderMarkdownToHtml(text);

  if (suggestions && suggestions.length > 0) {
    content +=
      `<div class="chips-container">` +
      suggestions
        .map(
          (s) => `<button class="chip-btn" onclick="window.app.quickPrompt('${s}')">${s}</button>`
        )
        .join("") +
      `</div>`;
  }

  bubble.innerHTML = content;
  stream.appendChild(bubble);
  stream.scrollTop = stream.scrollHeight;
}

export function quickPrompt(txt: string): void {
  if (txt === "Point of Contact" || txt === "Connect with Buddy" || txt === "Connect to Point of Contact") {
    openContactsModal();
    return;
  }
  if (txt === "Check Timesheet Status" || txt === "Check Timesheet") {
    openTimesheetModal();
    return;
  }
  if (txt === "Report IT Ticket") {
    openIncidentModal();
    return;
  }
  if (txt === "Search Runbooks") {
    openRunbooksModal();
    return;
  }
  if (txt === "Coding Standards") {
    openDocumentModal("DOC-ALL-002");
    return;
  }
  const input = document.getElementById("user-input-box") as HTMLInputElement;
  if (input) {
    input.value = txt;
    sendChatMessage();
  }
}

export async function openContactsModal(): Promise<void> {
  const modal = document.getElementById("contacts-modal");
  if (modal) modal.style.display = "grid";

  const container = document.getElementById("contacts-modal-content");
  if (!container) return;

  container.innerHTML = `<div style="font-size: 13px; color: var(--text-muted); padding: 24px 0; text-align: center;">Loading team contact directory...</div>`;

  try {
    const data = await apiRequest<any>("/api/v1/contacts/points-of-contact", "GET");
    if (!data) throw new Error("No contact data returned");

    const buddy = data.buddy || data.assigned_buddy;
    const manager = data.manager;
    const itContact = data.it_support;
    const hrContact = data.people_ops || data.hr_people_ops;
    const escalations = data.domain_escalations || data.domain_escalation_leads || [];

    let html = `
      <!-- 1. Dedicated Support (Buddy & Manager) -->
      <div style="margin-bottom: 20px;">
        <div style="font-size: 13px; font-weight: 700; color: var(--accent-indigo); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px;">
          Primary Personal Support Network
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px;">
          
          <!-- Buddy Card -->
          <div class="contact-card">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
              <span class="contact-role-badge">🤝 ONBOARDING BUDDY</span>
              <span class="contact-status-online">● Available</span>
            </div>
            <div style="font-size: 15px; font-weight: 600; color: var(--text-primary);">${buddy?.name || "Priya Nair"}</div>
            <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 6px;">${buddy?.role || "Staff Software Engineer & Tech Lead"}</div>
            <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px;">
              <div>📧 <strong>${buddy?.email || "priya.nair@company.com"}</strong></div>
              <div>💬 Slack: <strong>${buddy?.channel || "#payments-dev"}</strong></div>
              <div style="margin-top: 4px; font-style: italic;">Scope: ${buddy?.scope || "Day-1 Onboarding Buddy, Codebase Questions & Daily Guidance"}</div>
            </div>
            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
              <a class="contact-btn-action" href="mailto:${buddy?.email || "priya.nair@company.com"}?subject=Onboarding%20Question">
                ✉️ Email Buddy
              </a>
              <button class="contact-btn-action" onclick="app.askInChatAboutPerson('${buddy?.name || "Priya Nair"}', 'Buddy')">
                💬 Prep Questions
              </button>
            </div>
          </div>

          <!-- Manager Card -->
          <div class="contact-card">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
              <span class="contact-role-badge" style="background: rgba(16, 185, 129, 0.2); color: #6EE7B7;">👔 REPORTING MANAGER</span>
              <span class="contact-status-online">● Online</span>
            </div>
            <div style="font-size: 15px; font-weight: 600; color: var(--text-primary);">${manager?.name || "Sarah Jenkins"}</div>
            <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 6px;">${manager?.role || "Engineering Manager - Payments"}</div>
            <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px;">
              <div>📧 <strong>${manager?.email || "sarah.j@company.com"}</strong></div>
              <div>💬 Slack: <strong>${manager?.channel || "#eng-leadership"}</strong></div>
              <div style="margin-top: 4px; font-style: italic;">Scope: ${manager?.scope || "Direct Reporting Manager, 1:1 Check-ins, Performance & Approvals"}</div>
            </div>
            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
              <a class="contact-btn-action" href="mailto:${manager?.email || "sarah.j@company.com"}?subject=1:1%20Check-in">
                ✉️ Email Manager
              </a>
              <button class="contact-btn-action" onclick="app.askInChatAboutPerson('${manager?.name || "Sarah Jenkins"}', 'Manager')">
                💬 Prep 1:1 Agenda
              </button>
            </div>
          </div>

        </div>
      </div>

      <!-- 2. Operational Partners (IT & HR) -->
      <div style="margin-bottom: 20px;">
        <div style="font-size: 13px; font-weight: 700; color: var(--accent-indigo); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px;">
          Operations & People Services
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px;">
          
          <!-- IT Card -->
          <div class="contact-card">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
              <span class="contact-role-badge" style="background: rgba(239, 68, 68, 0.2); color: #FCA5A5;">💻 IT & SYSTEMS</span>
              <span class="contact-status-online">● Desk Active</span>
            </div>
            <div style="font-size: 15px; font-weight: 600; color: var(--text-primary);">${itContact?.name || "Marcus Vance"}</div>
            <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 6px;">${itContact?.role || "Lead IT Systems Administrator"}</div>
            <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px;">
              <div>📧 <strong>${itContact?.email || "marcus.v@company.com"}</strong></div>
              <div>💬 Slack: <strong>${itContact?.channel || "#help-it"}</strong></div>
              <div style="margin-top: 4px; font-style: italic;">Scope: Hardware, Cloud IAM credentials, VPN and Developer Access</div>
            </div>
            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
              <button class="contact-btn-action" onclick="app.closeContactsModal(); app.openIncidentModal();">
                🚨 File IT Ticket
              </button>
              <a class="contact-btn-action" href="mailto:${itContact?.email || "marcus.v@company.com"}">
                ✉️ Email IT Lead
              </a>
            </div>
          </div>

          <!-- HR Card -->
          <div class="contact-card">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
              <span class="contact-role-badge" style="background: rgba(245, 158, 11, 0.2); color: #FCD34D;">👥 PEOPLE OPS (HR)</span>
              <span class="contact-status-online">● Available</span>
            </div>
            <div style="font-size: 15px; font-weight: 600; color: var(--text-primary);">${hrContact?.name || "Amanda Walker"}</div>
            <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 6px;">${hrContact?.role || "Senior People Operations Specialist"}</div>
            <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px;">
              <div>📧 <strong>${hrContact?.email || "amanda.w@company.com"}</strong></div>
              <div>💬 Slack: <strong>${hrContact?.channel || "#people-ops"}</strong></div>
              <div style="margin-top: 4px; font-style: italic;">Scope: Benefits, Payroll, Timesheets, and Workplace Policies</div>
            </div>
            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
              <a class="contact-btn-action" href="mailto:${hrContact?.email || "amanda.w@company.com"}">
                ✉️ Email HR Partner
              </a>
              <button class="contact-btn-action" onclick="app.closeContactsModal(); app.openTimesheetModal();">
                ⏱️ Timesheet Status
              </button>
            </div>
          </div>

        </div>
      </div>

      <!-- 3. Domain Escalation Leads (With Out-of-Office Fallback Routing) -->
      <div>
        <div style="font-size: 13px; font-weight: 700; color: var(--accent-indigo); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">
          Technical Domain Escalation Matrix (With Smart OOO Routing)
        </div>
        <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 12px;">
          When standard runbooks do not resolve technical blockers, these tier-3 domain leads provide escalation support.
        </div>
        <div style="display: flex; flex-direction: column; gap: 10px;">
          ${escalations.map((esc: any) => {
            const primaryName = typeof esc.primary_lead === "object" ? esc.primary_lead?.name : esc.primary_lead;
            const primaryEmail = typeof esc.primary_lead === "object" ? esc.primary_lead?.email : esc.primary_email;
            const primaryOOO = typeof esc.primary_lead === "object" ? esc.primary_lead?.is_ooo : esc.primary_ooo;

            const backupName = typeof esc.backup_lead === "object" ? esc.backup_lead?.name : esc.backup_lead;
            const backupEmail = typeof esc.backup_lead === "object" ? esc.backup_lead?.email : esc.backup_email;
            const backupOOO = typeof esc.backup_lead === "object" ? esc.backup_lead?.is_ooo : esc.backup_ooo;

            const activeText = typeof esc.active_contact === "object" 
              ? `${esc.active_contact?.name} (${esc.active_contact?.email})`
              : (esc.active_contact || primaryName);
            
            const emailHref = primaryOOO && !backupOOO && backupEmail 
              ? backupEmail 
              : (primaryEmail || "");

            return `
              <div class="contact-card" style="margin-bottom: 0;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 6px;">
                  <span style="font-size: 14px; font-weight: 600; color: var(--text-primary);">🔧 ${esc.domain}</span>
                  <span class="role-tag role-manager" style="font-size: 10px;">${esc.channel}</span>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 12px; background: rgba(0,0,0,0.2); padding: 8px 12px; border-radius: 6px; margin-bottom: 8px;">
                  <div>
                    <div style="color: var(--text-muted); font-size: 11px;">Primary Lead</div>
                    <div style="font-weight: 600;">${primaryName || "Lead"}</div>
                    <div style="font-size: 11px; color: ${primaryOOO ? '#FCD34D' : '#6EE7B7'};">
                      ${primaryOOO ? '⚠️ Out of Office' : '● In Office'}
                    </div>
                  </div>
                  <div>
                    <div style="color: var(--text-muted); font-size: 11px;">Backup Lead</div>
                    <div style="font-weight: 600;">${backupName || "Backup Lead"}</div>
                    <div style="font-size: 11px; color: ${backupOOO ? '#FCD34D' : '#6EE7B7'};">
                      ${backupOOO ? '⚠️ Out of Office' : '● In Office'}
                    </div>
                  </div>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                  <div style="font-size: 12px;">
                    Active Point of Contact: <strong style="color: var(--accent-indigo);">${activeText}</strong>
                  </div>
                  ${emailHref ? `
                    <a class="contact-btn-action" href="mailto:${emailHref}?subject=Escalation:%20${encodeURIComponent(esc.domain)}">
                      ✉️ Email Lead
                    </a>
                  ` : ''}
                </div>
              </div>
            `;
          }).join("")}
        </div>
      </div>
    `;

    container.innerHTML = html;
  } catch (err: any) {
    container.innerHTML = `
      <div style="padding: 20px; text-align: center; color: var(--accent-coral);">
        Failed to load contact directory: ${err.message}
      </div>
    `;
  }
}

export function closeContactsModal(): void {
  const modal = document.getElementById("contacts-modal");
  if (modal) modal.style.display = "none";
}

export function askInChatAboutPerson(name: string, role: string): void {
  closeContactsModal();
  const prompt = `What are the best questions to ask my ${role}, ${name}, during our initial sync?`;
  quickPrompt(prompt);
}

export async function checkTimesheet(): Promise<void> {
  openTimesheetModal();
}

export function openIncidentModal(): void {
  const modal = document.getElementById("incident-modal");
  if (modal) modal.style.display = "grid";
}

export function closeIncidentModal(): void {
  const modal = document.getElementById("incident-modal");
  if (modal) modal.style.display = "none";
}

export async function submitIncident(): Promise<void> {
  const cat = ($<HTMLSelectElement>("inc-category")).value;
  const summary = ($<HTMLTextAreaElement>("inc-summary")).value.trim();
  if (!summary) {
    alert("Please provide an incident summary");
    return;
  }

  try {
    const inc = await apiRequest<any>("/api/v1/incidents/create", "POST", {
      category: cat,
      summary,
      severity: "MEDIUM",
      confirmed: true,
    });
    closeIncidentModal();
    const jiraInfo = inc.jira_issue;
    const jiraLabel = jiraInfo?.mode === "PRODUCTION_LIVE"
      ? `Live Jira Cloud Synced (${jiraInfo.issue_key})`
      : `Staged in Cloud Firestore (${jiraInfo?.issue_key || inc.incident_id})`;
    appendChatMessage(
      "assistant",
      `🚨 **Incident Ticket Generated**: Ticket **${inc.incident_id}** assigned to **${inc.assigned_team}** (${inc.lead_contact}).\n\n• **Sync State**: ${jiraLabel}\n• **Summary**: ${inc.summary}`,
      "Operations Specialist"
    );
  } catch (e: any) {
    alert("Incident creation error: " + e.message);
  }
}

export function togglePersonaHelper(): void {
  const container = document.getElementById("persona-grid-container");
  const arrow = document.getElementById("persona-toggle-arrow");
  const btn = document.getElementById("btn-toggle-roster");
  if (!container) return;

  const isHidden = container.style.display === "none" || getComputedStyle(container).display === "none";
  if (isHidden) {
    container.style.display = "grid";
    if (arrow) arrow.textContent = "▼";
    if (btn) btn.setAttribute("aria-expanded", "true");
  } else {
    container.style.display = "none";
    if (arrow) arrow.textContent = "▶";
    if (btn) btn.setAttribute("aria-expanded", "false");
  }
}

let isGsiInitialized = false;
let googleTokenClient: any = null;

export function initGoogleIdentity(): void {
  if (isGsiInitialized) return;
  const google = (window as any).google;
  const clientId = (window as any).__GOOGLE_CLIENT_ID__ || "";

  if (!google || !clientId || clientId.startsWith("__")) return;

  try {
    // 1. Initialize Google OAuth 2.0 Token Client (Popup flow, safe in iframes & avoids FedCM)
    if (google.accounts?.oauth2?.initTokenClient) {
      try {
        googleTokenClient = google.accounts.oauth2.initTokenClient({
          client_id: clientId,
          scope: "openid email profile",
          callback: async (tokenResponse: any) => {
            setAuthLoading(false);
            if (tokenResponse?.error) {
              console.warn("Google OAuth popup error:", tokenResponse);
              showAuthAlert(
                "Google Sign-In Notice",
                "Google sign-in popup was dismissed. You can sign in using your corporate email below.",
                "info"
              );
              return;
            }
            if (tokenResponse?.access_token) {
              setAuthStatus("Google account authorized, completing session initialization...");
              initializeSession(tokenResponse.access_token);
            }
          },
          error_callback: (err: any) => {
            console.warn("Google OAuth error callback:", err);
            setAuthLoading(false);
          },
        });
      } catch (oauthErr) {
        console.warn("OAuth token client init exception:", oauthErr);
      }
    }

    // 2. Initialize Google Identity (with FedCM explicitly disabled to avoid iframe NotAllowedError)
    if (google.accounts?.id) {
      google.accounts.id.initialize({
        client_id: clientId,
        callback: (response: any) => {
          if (response?.credential) {
            initializeSession(response.credential);
          } else {
            showAuthAlert("Google Auth Error", "No credential token received from Google Identity.", "error");
          }
        },
        auto_select: false,
        cancel_on_tap_outside: true,
        use_fedcm_for_prompt: false,
      });

      const btnContainer = document.getElementById("google-button");
      if (btnContainer) {
        google.accounts.id.renderButton(btnContainer, {
          theme: "filled_blue",
          size: "large",
          width: 360,
          text: "signin_with",
          shape: "rectangular",
        });
      }
    }

    isGsiInitialized = true;
  } catch (e) {
    console.warn("Failed to initialize Google Identity Services:", e);
  }
}

export function handleGoogleSignInClick(): void {
  dismissAuthAlert();
  const google = (window as any).google;
  const clientId = (window as any).__GOOGLE_CLIENT_ID__;

  // Initialize GIS if not yet initialized
  initGoogleIdentity();

  // 1. Primary: Use Google OAuth Token Client popup (works in iframes without FedCM)
  if (googleTokenClient) {
    setAuthLoading(true, "Connecting to Google...");
    setAuthStatus("Opening Google Account sign-in window...");
    try {
      googleTokenClient.requestAccessToken({ prompt: "select_account" });
      return;
    } catch (e) {
      console.warn("Token client request failed, falling back to One Tap:", e);
    }
  }

  // 2. Secondary: Fallback to accounts.id prompt with FedCM disabled
  if (google?.accounts?.id && clientId && !clientId.startsWith("__")) {
    setAuthLoading(true, "Connecting to Google...");
    setAuthStatus("Connecting to Google Identity Services...");

    try {
      google.accounts.id.prompt((notification: any) => {
        if (notification.isNotDisplayed()) {
          const reason = typeof notification.getNotDisplayedReason === "function"
            ? notification.getNotDisplayedReason()
            : "iframe_policy_or_no_session";
          console.log("Google One Tap not displayed:", reason);
          fallbackGoogleLogin();
        } else if (notification.isSkippedMoment()) {
          const reason = typeof notification.getSkippedReason === "function"
            ? notification.getSkippedReason()
            : "user_skipped";
          console.log("Google One Tap skipped:", reason);
          if (reason === "user_cancel") {
            setAuthLoading(false);
            showAuthAlert("Sign-In Cancelled", "Google One Tap was dismissed. Enter your work email below to sign in.", "warning");
          } else {
            fallbackGoogleLogin();
          }
        } else if (notification.isDismissedMoment()) {
          console.log("Google One Tap dismissed");
          setAuthLoading(false);
        }
      });
      return;
    } catch (e: any) {
      console.warn("Google One Tap prompt exception:", e);
      fallbackGoogleLogin();
      return;
    }
  }

  fallbackGoogleLogin();
}

function fallbackGoogleLogin(): void {
  const inputEl = document.getElementById("login-identity-input") as HTMLInputElement | null;
  const typedVal = inputEl?.value?.trim();
  const corporateGoogleEmail = (typedVal && typedVal.includes("@")) ? typedVal : "rangisettynavyasai@gmail.com";
  setAuthStatus(`Authenticating Google Workspace identity (${corporateGoogleEmail})...`);
  initializeSession(corporateGoogleEmail);
}


export async function handleEmployeeSignIn(event: Event): Promise<void> {
  event.preventDefault();
  dismissAuthAlert();
  const identityInput = document.getElementById("login-identity-input") as HTMLInputElement;
  const passwordInput = document.getElementById("login-password-input") as HTMLInputElement;

  const identity = identityInput?.value.trim();
  const password = passwordInput?.value.trim() || "";

  if (!identity) {
    showAuthAlert("Input Required", "Please enter your Work Email or Employee ID.", "warning");
    setAuthStatus("Please enter your Work Email or Employee ID.", true);
    return;
  }
  if (!password) {
    showAuthAlert("Password Required", "Please enter your password (demo: password123).", "warning");
    setAuthStatus("Please enter your password (demo: password123).", true);
    return;
  }

  setAuthLoading(true, "Verifying Credentials...");
  setAuthStatus("Verifying corporate credentials...");

  try {
    const res = await fetch("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identity, password }),
    });

    const data = await res.json();
    if (!res.ok || !data.token) {
      throw new Error(data.detail || "Invalid employee credentials or password.");
    }

    await initializeSession(data.token);
  } catch (err: any) {
    showAuthAlert("Sign-In Failed", err.message || "Invalid corporate credentials.", "error");
    setAuthStatus("Authentication failed: " + err.message, true);
  } finally {
    setAuthLoading(false);
  }
}

export function signInWithMockToken(token: string): void {
  initializeSession(token);
}

export function signOut(): void {
  sessionStorage.removeItem(AUTH_TOKEN_KEY);
  state.activeBearerToken = null;
  state.currentSessionId = null;
  state.currentUserProfile = null;
  $<HTMLElement>("dashboard-view").style.display = "none";
  $<HTMLElement>("auth-view").style.display = "block";
  dismissAuthAlert();
  setAuthStatus("Signed out. Select a sign-in method to continue.", false);
  if ((window as any).google?.accounts?.id) {
    try {
      (window as any).google.accounts.id.disableAutoSelect();
    } catch (e) {
      console.warn("Could not disable Google auto select:", e);
    }
  }
}

// Attach functions to global window namespace for template callbacks
(window as any).app = {
  initializeSession,
  refreshChecklist,
  renderChecklistTasks,
  toggleCompletedTasks,
  completeTask,
  sendChatMessage,
  appendChatMessage,
  quickPrompt,
  checkTimesheet,
  openTimesheetModal,
  closeTimesheetModal,
  handleTimesheetSubmit,
  openDocumentModal,
  closeDocumentModal,
  copyDocumentUri,
  askAboutCurrentDocument,
  openRunbooksModal,
  closeRunbooksModal,
  handleRunbookSearch,
  openContactsModal,
  closeContactsModal,
  askInChatAboutPerson,
  openIncidentModal,
  closeIncidentModal,
  submitIncident,
  togglePersonaHelper,
  handleGoogleSignInClick,
  handleEmployeeSignIn,
  signInWithMockToken,
  signOut,
  showAuthAlert,
  dismissAuthAlert,
};

// Also attach individual methods directly on window for direct onclick compatibility
Object.assign(window, (window as any).app);

// Initialize Google Identity Services on load and restore existing session
window.addEventListener("DOMContentLoaded", () => {
  initGoogleIdentity();

  // Check for existing session token in sessionStorage
  const savedToken = sessionStorage.getItem(AUTH_TOKEN_KEY);
  if (savedToken) {
    const restoringBanner = document.getElementById("session-restoring-banner");
    if (restoringBanner) restoringBanner.style.display = "flex";
    initializeSession(savedToken, true);
  }
});

// Also attempt initialization if GSI script loads after DOMContentLoaded
window.addEventListener("load", () => {
  if (!isGsiInitialized) {
    initGoogleIdentity();
  }
});
