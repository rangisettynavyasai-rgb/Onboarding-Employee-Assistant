"use strict";
(() => {
  var __defProp = Object.defineProperty;
  var __defNormalProp = (obj, key, value) => key in obj ? __defProp(obj, key, { enumerable: true, configurable: true, writable: true, value }) : obj[key] = value;
  var __publicField = (obj, key, value) => __defNormalProp(obj, typeof key !== "symbol" ? key + "" : key, value);

  // src/ui/app.ts
  var AppState = class {
    constructor() {
      __publicField(this, "activeBearerToken", null);
      __publicField(this, "currentSessionId", null);
      __publicField(this, "currentUserProfile", null);
      __publicField(this, "currentChecklistData", null);
      __publicField(this, "showCompletedTasks", true);
    }
  };
  var state = new AppState();
  function $(id) {
    const el = document.getElementById(id);
    if (!el) {
      throw new Error(`Element #${id} not found in DOM`);
    }
    return el;
  }
  function setAuthStatus(msg, isError = false) {
    const el = document.getElementById("auth-status");
    if (el) {
      el.textContent = msg;
      el.style.color = isError ? "var(--accent-rose)" : "var(--text-muted)";
    }
  }
  async function apiRequest(path, method = "GET", body = null) {
    const headers = {
      Authorization: `Bearer ${state.activeBearerToken}`
    };
    if (body) {
      headers["Content-Type"] = "application/json";
    }
    const resp = await fetch(path, {
      method,
      headers,
      body: body ? JSON.stringify(body) : null
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      throw new Error(data.message || data.detail || `HTTP Error ${resp.status}`);
    }
    return data;
  }
  async function initializeSession(token) {
    state.activeBearerToken = token;
    setAuthStatus("Authenticating corporate credentials...");
    try {
      const landing = await apiRequest("/api/v1/landing", "POST");
      state.currentUserProfile = landing;
      const sessionKey = `onboarding_session_${landing.employee_id}`;
      state.currentSessionId = localStorage.getItem(sessionKey) || `sess-${landing.employee_id.toLowerCase()}`;
      localStorage.setItem(sessionKey, state.currentSessionId);
      $("auth-view").style.display = "none";
      $("dashboard-view").style.display = "flex";
      $("user-display-name").textContent = landing.name;
      const teamEl = document.getElementById("user-display-team");
      if (teamEl) teamEl.textContent = `${landing.team} \u2022 ${landing.department}`;
      const roleEl = document.getElementById("user-display-role");
      if (roleEl) {
        roleEl.textContent = landing.authorization_role.toUpperCase();
        roleEl.className = `role-tag role-${landing.authorization_role.toLowerCase()}`;
      }
      $("proactive-greeting-text").textContent = landing.proactive_greeting;
      await refreshChecklist();
      await refreshKnowledgeInsights();
      await restoreSessionHistory(state.currentSessionId, landing.name);
    } catch (err) {
      setAuthStatus(err.message || "Failed to initialize session", true);
      state.activeBearerToken = null;
    }
  }
  async function restoreSessionHistory(sessionId, userName) {
    try {
      const sessionData = await apiRequest(
        `/api/v1/session/history?session_id=${sessionId}`
      );
      const stream = $("chat-stream");
      stream.innerHTML = "";
      if (sessionData.history && sessionData.history.length > 0) {
        sessionData.history.forEach((m) => {
          appendChatMessage(
            m.role,
            m.content,
            m.role === "assistant" ? m.agent || "Supervisor Agent" : null
          );
        });
      } else {
        appendChatMessage(
          "assistant",
          `\u{1F44B} Hello **${userName}**! I'm your secure AI Onboarding & Employee Assistant. How can I help you today?`,
          "Supervisor Agent",
          ["Check Timesheet", "View Pending Tasks", "Point of Contact", "Search Runbooks"]
        );
      }
    } catch (e) {
      console.warn("Could not load previous session history:", e);
      appendChatMessage(
        "assistant",
        `\u{1F44B} Hello **${userName}**! I'm your secure AI Onboarding & Employee Assistant. How can I help you today?`,
        "Supervisor Agent",
        ["Check Timesheet", "View Pending Tasks", "Point of Contact", "Search Runbooks"]
      );
    }
  }
  async function refreshKnowledgeInsights() {
    const container = document.getElementById("mesh-insights-container");
    if (!container) return;
    try {
      const data = await apiRequest(
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
          <span class="read-doc-badge">\u{1F4D6} Read Doc \u2192</span>
        </div>
      `;
        const docTarget = item.doc_id || item.document_id || item.insight_id || item.title;
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
  function toggleCompletedTasks(checked) {
    state.showCompletedTasks = checked;
    renderChecklistTasks();
  }
  function renderChecklistTasks() {
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
        ${!state.showCompletedTasks && completedTasks.length > 0 ? "All completed tasks hidden. Toggle switch above to view." : "No tasks found."}
      </div>
    `;
      return;
    }
    visibleTasks.forEach((t) => {
      const isDone = t.status === "COMPLETED";
      const isOverdue = !isDone && (t.is_overdue || t.due_date && t.due_date < "2026-09-07");
      const div = document.createElement("div");
      div.className = `task-item ${isDone ? "completed" : ""} ${isOverdue ? "overdue" : ""}`;
      const dueDateText = t.due_date ? `Due: ${t.due_date}` : `Due in +${t.due_days_after_start}d`;
      div.innerHTML = `
      <div style="flex: 1; min-width: 0;">
        <div style="font-weight: 600; font-size: 12px; color: ${isOverdue ? "#fda4af" : "var(--text-primary)"};">${t.title}</div>
        <div style="color: var(--text-muted); font-size: 10px; margin-top: 2px;">
          ${t.category} \u2022 ${t.task_id}
        </div>
        <div class="due-date-badge ${isOverdue ? "overdue-badge" : ""}">
          <span>${isOverdue ? "\u26A0\uFE0F Overdue:" : "\u{1F4C5}"}</span>
          <span>${dueDateText}</span>
        </div>
      </div>
      <div style="flex-shrink: 0; margin-left: 8px;">
        ${!isDone ? `<button class="task-btn-done" data-task-id="${t.task_id}" onclick="completeTask('${t.task_id}')">Done</button>` : `<span style="color: var(--accent-emerald); font-weight: 700; font-size: 14px;">\u2713</span>`}
      </div>
    `;
      const doneBtn = div.querySelector(".task-btn-done");
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
  async function refreshChecklist() {
    try {
      const checklist = await apiRequest("/api/v1/onboarding/my-status");
      state.currentChecklistData = checklist;
      const fill = $("progress-bar-fill");
      const pctEl = $("progress-percentage");
      const pct = Math.round(checklist.completed_count / checklist.total_count * 100) || 0;
      fill.style.width = pct + "%";
      pctEl.textContent = `${pct}% (${checklist.completed_count}/${checklist.total_count})`;
      renderChecklistTasks();
    } catch (e) {
      console.error("Checklist error:", e);
    }
  }
  async function completeTask(taskId) {
    try {
      await apiRequest("/api/v1/onboarding/complete-task", "POST", { task_id: taskId });
      await refreshChecklist();
      appendChatMessage(
        "assistant",
        `\u2705 Task **${taskId}** has been marked complete! Your onboarding checklist progress is now updated.`,
        "Onboarding Specialist"
      );
    } catch (err) {
      console.error("Task completion failed:", err);
      appendChatMessage(
        "assistant",
        `\u26A0\uFE0F Could not complete task **${taskId}**: ${err.message}`,
        "Onboarding Specialist"
      );
    }
  }
  function renderMarkdownToHtml(markdown) {
    if (!markdown) return "";
    function escape(t) {
      return t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }
    let text = markdown.replace(/```([\s\S]*?)```/g, (_m, code) => {
      return `<pre><code>${escape(code.trim())}</code></pre>`;
    }).replace(/`([^`]+)`/g, (_m, code) => {
      return `<code>${escape(code)}</code>`;
    }).replace(/^### (.*$)/gim, "<h3>$1</h3>").replace(/^## (.*$)/gim, "<h2>$1</h2>").replace(/^# (.*$)/gim, "<h1>$1</h1>").replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>").replace(/\*(.*?)\*/g, "<em>$1</em>").replace(/^\s*-\s+(.*$)/gim, "<li>$1</li>").replace(/^\s*\d+\.\s+(.*$)/gim, "<li>$1</li>").replace(/\n\n+/g, "<br><br>").replace(/\n/g, "<br>");
    return text;
  }
  var currentActiveDocument = null;
  async function openDocumentModal(docId) {
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
      const doc = await apiRequest(`/api/v1/documents/${encodeURIComponent(docId)}`);
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
    } catch (err) {
      if (titleEl) titleEl.textContent = "Error Loading Document";
      if (contentEl) contentEl.innerHTML = `<div style="padding: 24px; color: var(--accent-rose);">Failed to retrieve document: ${err.message}</div>`;
    }
  }
  function closeDocumentModal() {
    const modal = document.getElementById("document-modal");
    if (modal) modal.style.display = "none";
  }
  function copyDocumentUri() {
    if (!currentActiveDocument?.gcs_uri) return;
    navigator.clipboard.writeText(currentActiveDocument.gcs_uri).then(() => {
      const btn = document.getElementById("doc-copy-uri-btn");
      if (btn) {
        const original = btn.textContent;
        btn.textContent = "\u2713 Copied!";
        setTimeout(() => {
          if (btn) btn.textContent = original;
        }, 2e3);
      }
    }).catch(() => {
    });
  }
  function askAboutCurrentDocument() {
    if (!currentActiveDocument) return;
    const docTitle = currentActiveDocument.title;
    const docId = currentActiveDocument.document_id;
    closeDocumentModal();
    quickPrompt(`Tell me more about the standards and procedures in ${docTitle} (${docId})`);
  }
  async function openTimesheetModal() {
    const modal = document.getElementById("timesheet-modal");
    if (!modal) return;
    modal.style.display = "grid";
    const feedback = document.getElementById("ts-feedback");
    if (feedback) feedback.textContent = "";
    try {
      const ts = await apiRequest("/api/v1/timesheets/my-status");
      const cycleEl = document.getElementById("ts-modal-cycle");
      const statusPill = document.getElementById("ts-modal-status-pill");
      const hoursInput = document.getElementById("ts-hours-input");
      if (cycleEl) cycleEl.textContent = `Period: ${ts.period_end || ts.period}`;
      if (statusPill) {
        statusPill.textContent = ts.status.toUpperCase();
        statusPill.className = ts.status.toUpperCase() === "SUBMITTED" || ts.status.toUpperCase() === "APPROVED" ? "status-pill-submitted" : "status-pill-pending";
      }
      if (hoursInput && ts.hours_logged) {
        hoursInput.value = String(ts.hours_logged);
      }
    } catch (err) {
      console.warn("Could not fetch timesheet status:", err);
    }
  }
  function closeTimesheetModal() {
    const modal = document.getElementById("timesheet-modal");
    if (modal) modal.style.display = "none";
  }
  async function handleTimesheetSubmit(event) {
    event.preventDefault();
    const hoursInput = document.getElementById("ts-hours-input");
    const notesInput = document.getElementById("ts-notes-input");
    const submitBtn = document.getElementById("ts-submit-btn");
    const feedback = document.getElementById("ts-feedback");
    const hours = parseFloat(hoursInput?.value || "40.0");
    const notes = notesInput?.value.trim() || "";
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = "Submitting...";
    }
    try {
      const result = await apiRequest("/api/v1/timesheets/submit", "POST", { hours, notes });
      if (feedback) {
        feedback.style.color = "var(--accent-emerald)";
        feedback.textContent = `\u2713 Timesheet submitted successfully! (${result.hours_logged} hours logged).`;
      }
      const statusPill = document.getElementById("ts-modal-status-pill");
      if (statusPill) {
        statusPill.textContent = "SUBMITTED";
        statusPill.className = "status-pill-submitted";
      }
      appendChatMessage(
        "assistant",
        `\u23F1\uFE0F **Timesheet Submitted**: Logged **${hours} hours** for the week. Status updated to **SUBMITTED** for automated payroll processing.`,
        "Operations Specialist"
      );
      setTimeout(() => {
        closeTimesheetModal();
      }, 1500);
    } catch (err) {
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
  var cachedRunbooks = [];
  async function openRunbooksModal() {
    const modal = document.getElementById("runbooks-modal");
    if (!modal) return;
    modal.style.display = "grid";
    const container = document.getElementById("runbooks-list-container");
    const searchInput = document.getElementById("runbooks-search-input");
    if (searchInput) searchInput.value = "";
    if (container) {
      container.innerHTML = "<div style='text-align:center; padding: 24px; color: var(--text-muted);'>Loading runbooks...</div>";
    }
    try {
      const res = await apiRequest("/api/v1/documents/all");
      cachedRunbooks = res.documents || [];
      renderRunbooksList(cachedRunbooks);
    } catch (err) {
      if (container) {
        container.innerHTML = `<div style="color: var(--accent-rose); padding: 16px;">Failed to load documents: ${err.message}</div>`;
      }
    }
  }
  function closeRunbooksModal() {
    const modal = document.getElementById("runbooks-modal");
    if (modal) modal.style.display = "none";
  }
  function handleRunbookSearch(query) {
    const q = query.toLowerCase().trim();
    if (!q) {
      renderRunbooksList(cachedRunbooks);
      return;
    }
    const filtered = cachedRunbooks.filter((doc) => {
      return doc.title && doc.title.toLowerCase().includes(q) || doc.document_id && doc.document_id.toLowerCase().includes(q) || doc.category && doc.category.toLowerCase().includes(q) || doc.team && doc.team.toLowerCase().includes(q) || doc.description && doc.description.toLowerCase().includes(q);
    });
    renderRunbooksList(filtered);
  }
  function renderRunbooksList(docs) {
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
        <span class="read-doc-badge">Read Full Document \u2192</span>
      </div>
    `;
      card.onclick = () => {
        closeRunbooksModal();
        openDocumentModal(doc.document_id);
      };
      container.appendChild(card);
    });
  }
  async function sendChatMessage() {
    const input = $("user-input-box");
    const msg = input.value.trim();
    if (!msg) return;
    input.value = "";
    appendChatMessage("user", msg);
    const btn = $("send-button");
    btn.disabled = true;
    try {
      const res = await apiRequest("/api/v1/chat", "POST", {
        message: msg,
        session_id: state.currentSessionId
      });
      state.currentSessionId = res.session_id;
      appendChatMessage(
        "assistant",
        res.response,
        res.agent_invoked,
        res.suggested_actions
      );
    } catch (err) {
      appendChatMessage("assistant", `\u26A0\uFE0F Error: ${err.message}`, "Security Guard");
    } finally {
      btn.disabled = false;
    }
  }
  function appendChatMessage(role, text, agentName = null, suggestions = []) {
    const stream = document.getElementById("chat-stream");
    if (!stream) return;
    const bubble = document.createElement("div");
    bubble.className = `message-bubble ${role === "user" ? "user-message" : "assistant-message"}`;
    let content = "";
    if (role === "assistant" && agentName) {
      content += `<div class="agent-badge-tag">\u26A1 ${agentName}</div><br>`;
    }
    content += renderMarkdownToHtml(text);
    if (suggestions && suggestions.length > 0) {
      content += `<div class="chips-container">` + suggestions.map(
        (s) => `<button class="chip-btn" onclick="window.app.quickPrompt('${s}')">${s}</button>`
      ).join("") + `</div>`;
    }
    bubble.innerHTML = content;
    stream.appendChild(bubble);
    stream.scrollTop = stream.scrollHeight;
  }
  function quickPrompt(txt) {
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
    const input = document.getElementById("user-input-box");
    if (input) {
      input.value = txt;
      sendChatMessage();
    }
  }
  async function openContactsModal() {
    const modal = document.getElementById("contacts-modal");
    if (modal) modal.style.display = "grid";
    const container = document.getElementById("contacts-modal-content");
    if (!container) return;
    container.innerHTML = `<div style="font-size: 13px; color: var(--text-muted); padding: 24px 0; text-align: center;">Loading team contact directory...</div>`;
    try {
      const data = await apiRequest("/api/v1/contacts/points-of-contact", "GET");
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
              <span class="contact-role-badge">\u{1F91D} ONBOARDING BUDDY</span>
              <span class="contact-status-online">\u25CF Available</span>
            </div>
            <div style="font-size: 15px; font-weight: 600; color: var(--text-primary);">${buddy?.name || "Priya Nair"}</div>
            <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 6px;">${buddy?.role || "Staff Software Engineer & Tech Lead"}</div>
            <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px;">
              <div>\u{1F4E7} <strong>${buddy?.email || "priya.nair@company.com"}</strong></div>
              <div>\u{1F4AC} Slack: <strong>${buddy?.channel || "#payments-dev"}</strong></div>
              <div style="margin-top: 4px; font-style: italic;">Scope: ${buddy?.scope || "Day-1 Onboarding Buddy, Codebase Questions & Daily Guidance"}</div>
            </div>
            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
              <a class="contact-btn-action" href="mailto:${buddy?.email || "priya.nair@company.com"}?subject=Onboarding%20Question">
                \u2709\uFE0F Email Buddy
              </a>
              <button class="contact-btn-action" onclick="app.askInChatAboutPerson('${buddy?.name || "Priya Nair"}', 'Buddy')">
                \u{1F4AC} Prep Questions
              </button>
            </div>
          </div>

          <!-- Manager Card -->
          <div class="contact-card">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
              <span class="contact-role-badge" style="background: rgba(16, 185, 129, 0.2); color: #6EE7B7;">\u{1F454} REPORTING MANAGER</span>
              <span class="contact-status-online">\u25CF Online</span>
            </div>
            <div style="font-size: 15px; font-weight: 600; color: var(--text-primary);">${manager?.name || "Sarah Jenkins"}</div>
            <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 6px;">${manager?.role || "Engineering Manager - Payments"}</div>
            <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px;">
              <div>\u{1F4E7} <strong>${manager?.email || "sarah.j@company.com"}</strong></div>
              <div>\u{1F4AC} Slack: <strong>${manager?.channel || "#eng-leadership"}</strong></div>
              <div style="margin-top: 4px; font-style: italic;">Scope: ${manager?.scope || "Direct Reporting Manager, 1:1 Check-ins, Performance & Approvals"}</div>
            </div>
            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
              <a class="contact-btn-action" href="mailto:${manager?.email || "sarah.j@company.com"}?subject=1:1%20Check-in">
                \u2709\uFE0F Email Manager
              </a>
              <button class="contact-btn-action" onclick="app.askInChatAboutPerson('${manager?.name || "Sarah Jenkins"}', 'Manager')">
                \u{1F4AC} Prep 1:1 Agenda
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
              <span class="contact-role-badge" style="background: rgba(239, 68, 68, 0.2); color: #FCA5A5;">\u{1F4BB} IT & SYSTEMS</span>
              <span class="contact-status-online">\u25CF Desk Active</span>
            </div>
            <div style="font-size: 15px; font-weight: 600; color: var(--text-primary);">${itContact?.name || "Marcus Vance"}</div>
            <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 6px;">${itContact?.role || "Lead IT Systems Administrator"}</div>
            <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px;">
              <div>\u{1F4E7} <strong>${itContact?.email || "marcus.v@company.com"}</strong></div>
              <div>\u{1F4AC} Slack: <strong>${itContact?.channel || "#help-it"}</strong></div>
              <div style="margin-top: 4px; font-style: italic;">Scope: Hardware, Cloud IAM credentials, VPN and Developer Access</div>
            </div>
            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
              <button class="contact-btn-action" onclick="app.closeContactsModal(); app.openIncidentModal();">
                \u{1F6A8} File IT Ticket
              </button>
              <a class="contact-btn-action" href="mailto:${itContact?.email || "marcus.v@company.com"}">
                \u2709\uFE0F Email IT Lead
              </a>
            </div>
          </div>

          <!-- HR Card -->
          <div class="contact-card">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
              <span class="contact-role-badge" style="background: rgba(245, 158, 11, 0.2); color: #FCD34D;">\u{1F465} PEOPLE OPS (HR)</span>
              <span class="contact-status-online">\u25CF Available</span>
            </div>
            <div style="font-size: 15px; font-weight: 600; color: var(--text-primary);">${hrContact?.name || "Amanda Walker"}</div>
            <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 6px;">${hrContact?.role || "Senior People Operations Specialist"}</div>
            <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px;">
              <div>\u{1F4E7} <strong>${hrContact?.email || "amanda.w@company.com"}</strong></div>
              <div>\u{1F4AC} Slack: <strong>${hrContact?.channel || "#people-ops"}</strong></div>
              <div style="margin-top: 4px; font-style: italic;">Scope: Benefits, Payroll, Timesheets, and Workplace Policies</div>
            </div>
            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
              <a class="contact-btn-action" href="mailto:${hrContact?.email || "amanda.w@company.com"}">
                \u2709\uFE0F Email HR Partner
              </a>
              <button class="contact-btn-action" onclick="app.closeContactsModal(); app.openTimesheetModal();">
                \u23F1\uFE0F Timesheet Status
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
          ${escalations.map((esc) => {
        const primaryName = typeof esc.primary_lead === "object" ? esc.primary_lead?.name : esc.primary_lead;
        const primaryEmail = typeof esc.primary_lead === "object" ? esc.primary_lead?.email : esc.primary_email;
        const primaryOOO = typeof esc.primary_lead === "object" ? esc.primary_lead?.is_ooo : esc.primary_ooo;
        const backupName = typeof esc.backup_lead === "object" ? esc.backup_lead?.name : esc.backup_lead;
        const backupEmail = typeof esc.backup_lead === "object" ? esc.backup_lead?.email : esc.backup_email;
        const backupOOO = typeof esc.backup_lead === "object" ? esc.backup_lead?.is_ooo : esc.backup_ooo;
        const activeText = typeof esc.active_contact === "object" ? `${esc.active_contact?.name} (${esc.active_contact?.email})` : esc.active_contact || primaryName;
        const emailHref = primaryOOO && !backupOOO && backupEmail ? backupEmail : primaryEmail || "";
        return `
              <div class="contact-card" style="margin-bottom: 0;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 6px;">
                  <span style="font-size: 14px; font-weight: 600; color: var(--text-primary);">\u{1F527} ${esc.domain}</span>
                  <span class="role-tag role-manager" style="font-size: 10px;">${esc.channel}</span>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 12px; background: rgba(0,0,0,0.2); padding: 8px 12px; border-radius: 6px; margin-bottom: 8px;">
                  <div>
                    <div style="color: var(--text-muted); font-size: 11px;">Primary Lead</div>
                    <div style="font-weight: 600;">${primaryName || "Lead"}</div>
                    <div style="font-size: 11px; color: ${primaryOOO ? "#FCD34D" : "#6EE7B7"};">
                      ${primaryOOO ? "\u26A0\uFE0F Out of Office" : "\u25CF In Office"}
                    </div>
                  </div>
                  <div>
                    <div style="color: var(--text-muted); font-size: 11px;">Backup Lead</div>
                    <div style="font-weight: 600;">${backupName || "Backup Lead"}</div>
                    <div style="font-size: 11px; color: ${backupOOO ? "#FCD34D" : "#6EE7B7"};">
                      ${backupOOO ? "\u26A0\uFE0F Out of Office" : "\u25CF In Office"}
                    </div>
                  </div>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                  <div style="font-size: 12px;">
                    Active Point of Contact: <strong style="color: var(--accent-indigo);">${activeText}</strong>
                  </div>
                  ${emailHref ? `
                    <a class="contact-btn-action" href="mailto:${emailHref}?subject=Escalation:%20${encodeURIComponent(esc.domain)}">
                      \u2709\uFE0F Email Lead
                    </a>
                  ` : ""}
                </div>
              </div>
            `;
      }).join("")}
        </div>
      </div>
    `;
      container.innerHTML = html;
    } catch (err) {
      container.innerHTML = `
      <div style="padding: 20px; text-align: center; color: var(--accent-coral);">
        Failed to load contact directory: ${err.message}
      </div>
    `;
    }
  }
  function closeContactsModal() {
    const modal = document.getElementById("contacts-modal");
    if (modal) modal.style.display = "none";
  }
  function askInChatAboutPerson(name, role) {
    closeContactsModal();
    const prompt = `What are the best questions to ask my ${role}, ${name}, during our initial sync?`;
    quickPrompt(prompt);
  }
  async function checkTimesheet() {
    openTimesheetModal();
  }
  function openIncidentModal() {
    const modal = document.getElementById("incident-modal");
    if (modal) modal.style.display = "grid";
  }
  function closeIncidentModal() {
    const modal = document.getElementById("incident-modal");
    if (modal) modal.style.display = "none";
  }
  async function submitIncident() {
    const cat = $("inc-category").value;
    const summary = $("inc-summary").value.trim();
    if (!summary) {
      alert("Please provide an incident summary");
      return;
    }
    try {
      const inc = await apiRequest("/api/v1/incidents/create", "POST", {
        category: cat,
        summary,
        severity: "MEDIUM",
        confirmed: true
      });
      closeIncidentModal();
      appendChatMessage(
        "assistant",
        `\u{1F6A8} **Incident Created**: Ticket **${inc.incident_id}** assigned to **${inc.assigned_team}**. Status: ${inc.status}.`,
        "Operations Action"
      );
    } catch (e) {
      alert("Incident creation error: " + e.message);
    }
  }
  function togglePersonaHelper() {
    const container = document.getElementById("persona-grid-container");
    const arrow = document.getElementById("persona-toggle-arrow");
    const btn = document.getElementById("btn-toggle-roster");
    if (!container) return;
    const isHidden = container.style.display === "none" || getComputedStyle(container).display === "none";
    if (isHidden) {
      container.style.display = "grid";
      if (arrow) arrow.textContent = "\u25BC";
      if (btn) btn.setAttribute("aria-expanded", "true");
    } else {
      container.style.display = "none";
      if (arrow) arrow.textContent = "\u25B6";
      if (btn) btn.setAttribute("aria-expanded", "false");
    }
  }
  function handleGoogleSignInClick() {
    const google = window.google;
    const clientId = window.__GOOGLE_CLIENT_ID__;
    setAuthStatus("Connecting to Google Identity...");
    if (google?.accounts?.id && clientId && !clientId.startsWith("__")) {
      try {
        google.accounts.id.prompt((notification) => {
          if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
            fallbackGoogleLogin();
          }
        });
        return;
      } catch (e) {
        console.warn("Google One Tap prompt error:", e);
        fallbackGoogleLogin();
        return;
      }
    }
    fallbackGoogleLogin();
  }
  function fallbackGoogleLogin() {
    setAuthStatus("Authenticating with Google Workspace identity...");
    const defaultGoogleIdentity = "rnavyasai@gmail.com";
    initializeSession(defaultGoogleIdentity);
  }
  async function handleEmployeeSignIn(event) {
    event.preventDefault();
    const identityInput = document.getElementById("login-identity-input");
    const passwordInput = document.getElementById("login-password-input");
    const identity = identityInput?.value.trim();
    const password = passwordInput?.value.trim() || "";
    if (!identity) {
      setAuthStatus("Please enter your Work Email or Employee ID.", true);
      return;
    }
    if (!password) {
      setAuthStatus("Please enter your password (demo: password123).", true);
      return;
    }
    const btn = document.getElementById("btn-employee-login");
    if (btn) {
      btn.disabled = true;
      btn.textContent = "Verifying Credentials...";
    }
    setAuthStatus("Verifying corporate credentials...");
    try {
      const res = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ identity, password })
      });
      const data = await res.json();
      if (!res.ok || !data.token) {
        throw new Error(data.detail || "Invalid employee credentials or password.");
      }
      await initializeSession(data.token);
    } catch (err) {
      setAuthStatus("Authentication failed: " + err.message, true);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = "Sign In";
      }
    }
  }
  function signInWithMockToken(token) {
    initializeSession(token);
  }
  function signOut() {
    state.activeBearerToken = null;
    state.currentSessionId = null;
    state.currentUserProfile = null;
    $("dashboard-view").style.display = "none";
    $("auth-view").style.display = "block";
    setAuthStatus("Signed out. Select a sign-in method to continue.");
    if (window.google?.accounts?.id) {
      window.google.accounts.id.disableAutoSelect();
    }
  }
  window.app = {
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
    signOut
  };
  Object.assign(window, window.app);
  window.addEventListener("DOMContentLoaded", () => {
    const clientId = window.__GOOGLE_CLIENT_ID__ || "";
    if (window.google?.accounts?.id && clientId && !clientId.startsWith("__")) {
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: (response) => {
          initializeSession(response.credential);
        },
        auto_select: false
      });
      const btnContainer = document.getElementById("google-button");
      if (btnContainer) {
        window.google.accounts.id.renderButton(btnContainer, {
          theme: "filled_blue",
          size: "large",
          width: 360,
          text: "signin_with",
          shape: "rectangular"
        });
      }
    }
  });
})();
