/* ============================================================
   Agora AI — Frontend Logic
   SSE streaming from FastAPI, agent rendering, UI state
   ============================================================ */

const API_BASE = "http://localhost:8080";

// ── State ──────────────────────────────────────────────────
let currentMode = "debate";
let activeMessage = null;   // { el, bodyEl, cursorEl, text }
let currentRound = 0;
let isDebating = false;

// ── DOM refs ───────────────────────────────────────────────
const topicInput        = document.getElementById("topicInput");
const charCount         = document.getElementById("charCount");
const startBtn          = document.getElementById("startBtn");
const heroSection       = document.getElementById("heroSection");
const arenaSection      = document.getElementById("arenaSection");
const arenaTopicText    = document.getElementById("arenaTopicText");
const arenaModeBadge    = document.getElementById("arenaModeBadge");
const messagesContainer = document.getElementById("messagesContainer");
const thinkingIndicator = document.getElementById("thinkingIndicator");
const thinkingIcon      = document.getElementById("thinkingIcon");
const thinkingAgentName = document.getElementById("thinkingAgentName");
const verdictBanner     = document.getElementById("verdictBanner");
const statusDot         = document.getElementById("statusDot");
const statusText        = document.getElementById("statusText");
const stepperFill       = document.getElementById("stepperFill");
const agentsLegend      = document.getElementById("agentsLegend");
const clarifierSection  = document.getElementById("clarifierSection");
const clarifierInput    = document.getElementById("clarifierInput");
const clarifierThinking = document.getElementById("clarifierThinking");
const confirmClarifierBtn = document.getElementById("confirmClarifierBtn");

// ── Init ───────────────────────────────────────────────────
window.addEventListener("DOMContentLoaded", () => {
  checkHealth();
  topicInput.addEventListener("input", onTopicInput);
  topicInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) startDebate();
  });
});

// ── Health check ───────────────────────────────────────────
async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/health`, { signal: AbortSignal.timeout(4000) });
    if (res.ok) {
      setStatus("online", "API Ready");
    } else {
      setStatus("error", "API Error");
    }
  } catch {
    setStatus("error", "Offline — Start backend");
  }
}

function setStatus(state, text) {
  statusDot.className = "status-dot " + state;
  statusText.textContent = text;
}

// ── Mode toggle ────────────────────────────────────────────
function setMode(mode) {
  currentMode = mode;

  document.querySelectorAll(".mode-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.mode === mode);
    btn.setAttribute("aria-selected", btn.dataset.mode === mode);
  });

  // Update placeholder and label
  const topicLabel = document.getElementById("topicLabel");
  if (mode === "debate") {
    topicInput.placeholder = "e.g., Should AI replace human jobs in the next decade?";
    topicLabel.textContent = "Debate Topic";
  } else {
    topicInput.placeholder = "e.g., I need to decide whether to leave my stable job to start a company";
    topicLabel.textContent = "Situation / Dilemma";
  }

  // Show/hide example chips
  document.querySelectorAll(".example-chip:not(.situation-chip)").forEach(c =>
    c.classList.toggle("hidden", mode === "situation"));
  document.querySelectorAll(".situation-chip").forEach(c =>
    c.classList.toggle("hidden", mode === "debate"));
}

// ── Input handler ──────────────────────────────────────────
function onTopicInput() {
  const len = topicInput.value.length;
  charCount.textContent = `${len} / 1000`;
  charCount.style.color = len > 900 ? "#ff6b6b" : "";
}

// ── Example inserts ────────────────────────────────────────
function setExample(text) {
  topicInput.value = text;
  onTopicInput();
  topicInput.focus();
}

// ── Start debate ───────────────────────────────────────────
async function startDebate() {
  const topic = topicInput.value.trim();
  if (!topic || topic.length < 5) {
    topicInput.classList.add("shake");
    setTimeout(() => topicInput.classList.remove("shake"), 500);
    topicInput.focus();
    return;
  }
  if (isDebating) return;

  if (currentMode === "situation") {
    startClarification(topic);
  } else {
    startDebateFlow(topic);
  }
}

async function startClarification(topic) {
  isDebating = true;
  startBtn.disabled = true;
  startBtn.querySelector("span:last-child").textContent = "Clarifying…";

  heroSection.style.display = "none";
  clarifierSection.style.display = "block";
  agentsLegend.style.display = "none";
  
  clarifierInput.value = "";
  clarifierThinking.style.display = "flex";
  confirmClarifierBtn.disabled = true;

  const personality = document.getElementById("personalitySelect").value;

  try {
    const response = await fetch(`${API_BASE}/api/clarify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic, personality }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: "Unknown error" }));
      clarifierInput.value = "Error: " + (err.detail || "Server error.");
      clarifierThinking.style.display = "none";
      confirmClarifierBtn.disabled = false;
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buf += decoder.decode(value, { stream: true });
      const lines = buf.split("\n\n");
      buf = lines.pop();

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        try {
          const evt = JSON.parse(line.slice(6));
          if (evt.type === "agent_chunk") {
            clarifierInput.value += evt.chunk;
          } else if (evt.type === "error") {
            clarifierInput.value += "\n\n" + evt.message;
          } else if (evt.type === "agent_end") {
            clarifierThinking.style.display = "none";
            confirmClarifierBtn.disabled = false;
          }
        } catch (e) {}
      }
    }
  } catch (err) {
    clarifierInput.value = "Connection failed. Is the backend running?";
    clarifierThinking.style.display = "none";
    confirmClarifierBtn.disabled = false;
  }
}

function cancelClarification() {
  clarifierSection.style.display = "none";
  resetDebate();
}

function confirmClarification() {
  const refinedTopic = clarifierInput.value.trim();
  if (!refinedTopic) return;
  clarifierSection.style.display = "none";
  startDebateFlow(refinedTopic);
}

async function startDebateFlow(topic) {
  const personality = document.getElementById("personalitySelect").value;

  isDebating = true;
  startBtn.disabled = true;
  startBtn.querySelector("span:last-child").textContent = "Debating…";

  // Show arena, hide hero
  heroSection.style.display = "none";
  arenaSection.style.display = "block";
  agentsLegend.style.display = "none";
  window.scrollTo({ top: 0, behavior: "smooth" });

  // Set arena meta
  arenaTopicText.textContent = topic;
  arenaModeBadge.textContent = currentMode === "debate" ? "⚔️ Debate Mode" : "🔮 Situation Analysis";
  verdictBanner.style.display = "none";
  messagesContainer.innerHTML = "";

  // Reset stepper
  for (let i = 1; i <= 4; i++) {
    const s = document.getElementById(`step${i}`);
    s.classList.remove("active", "complete");
  }
  stepperFill.style.width = "0%";
  currentRound = 0;

  // SSE stream
  try {
    const response = await fetch(`${API_BASE}/api/debate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic, mode: currentMode, rounds: 4, personality }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: "Unknown error" }));
      showError(err.detail || "Server error. Check your API key.");
      resetUI();
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buf += decoder.decode(value, { stream: true });
      const lines = buf.split("\n\n");
      buf = lines.pop(); // keep incomplete chunk

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        try {
          const evt = JSON.parse(line.slice(6));
          handleEvent(evt);
        } catch (e) {
          console.warn("Parse error:", e, line);
        }
      }
    }
  } catch (err) {
    showError("Connection failed. Is the backend running?\n\nRun: python -m uvicorn backend.main:app --reload");
    resetUI();
  }
}

// ── SSE event handler ──────────────────────────────────────
function handleEvent(evt) {
  switch (evt.type) {
    case "agent_start":
      handleAgentStart(evt);
      break;
    case "agent_chunk":
      handleAgentChunk(evt);
      break;
    case "agent_end":
      handleAgentEnd(evt);
      break;
    case "debate_end":
      handleDebateEnd(evt);
      break;
    case "error":
      showError(evt.message || "An error occurred.");
      resetUI();
      break;
  }
}

function handleAgentStart(evt) {
  // Update round stepper
  if (evt.round !== currentRound) {
    if (currentRound > 0) {
      const prev = document.getElementById(`step${currentRound}`);
      if (prev) { prev.classList.remove("active"); prev.classList.add("complete"); }
    }
    currentRound = evt.round;
    const step = document.getElementById(`step${currentRound}`);
    if (step) step.classList.add("active");
    // Stepper fill: round 1→25%, 2→50%, 3→75%, 4→100%
    stepperFill.style.width = `${(currentRound - 1) * 33.33}%`;
  }

  // Show thinking indicator with model info
  thinkingIcon.textContent = evt.icon || "🤖";
  const modelHint = evt.model_label ? ` (${evt.model_label})` : "";
  thinkingAgentName.textContent = (evt.agent || "Agent") + " is thinking" + modelHint;
  thinkingIndicator.style.display = "flex";

  // Create message card
  const isJudge = evt.agent && evt.agent.toLowerCase().includes("judge");
  const card = document.createElement("div");
  card.className = "agent-message" + (isJudge ? " judge-card" : "");
  card.style.setProperty("--agent-color", evt.color || "#7c3aed");
  card.setAttribute("data-agent", evt.agent);

  const msgId = `msg-${Date.now()}`;

  card.innerHTML = `
    <div class="agent-message-header" onclick="toggleMessage('${msgId}')">
      <div class="agent-icon" style="border-color:${evt.color}30; background:${evt.color}18; color:${evt.color}">${evt.icon || "🤖"}</div>
      <div class="agent-header-info">
        <div class="agent-name" style="color:${evt.color}">${escHtml(evt.agent)}</div>
        <div class="agent-role">${escHtml(evt.role || "")}</div>
      </div>
      ${evt.model_label ? `<div class="agent-model-badge">${evt.model_icon || "🤖"} ${escHtml(evt.model_label)}</div>` : ""}
      <div class="round-badge">${escHtml(evt.round_label || `Round ${evt.round}`)}</div>
      <button class="msg-collapse-btn" id="collapseBtn-${msgId}" aria-label="Collapse message">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <path d="m18 15-6-6-6 6"/>
        </svg>
      </button>
    </div>
    <div class="agent-message-body" id="body-${msgId}"></div>
    <div class="msg-footer" id="footer-${msgId}" style="display:none">
      <button class="copy-btn" id="copy-${msgId}" onclick="copyMessage('${msgId}')">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
        </svg>
        Copy
      </button>
    </div>
  `;

  messagesContainer.appendChild(card);

  const bodyEl = document.getElementById(`body-${msgId}`);
  // Blinking cursor
  const cursorEl = document.createElement("span");
  cursorEl.className = "cursor-blink";
  bodyEl.appendChild(cursorEl);

  activeMessage = { el: card, bodyEl, cursorEl, text: "", msgId };

  // Scroll to card
  setTimeout(() => card.scrollIntoView({ behavior: "smooth", block: "nearest" }), 100);
}

function handleAgentChunk(evt) {
  if (!activeMessage) return;
  activeMessage.text += evt.chunk;

  // Render as formatted HTML (simple markdown-like)
  const { bodyEl, cursorEl } = activeMessage;
  bodyEl.innerHTML = renderMarkdown(activeMessage.text);
  bodyEl.appendChild(cursorEl); // re-attach cursor at end
}

function handleAgentEnd(evt) {
  if (!activeMessage) return;

  const { bodyEl, cursorEl, msgId, text } = activeMessage;

  // Remove cursor, finalize text
  if (cursorEl.parentNode) cursorEl.parentNode.removeChild(cursorEl);
  bodyEl.innerHTML = renderMarkdown(text);

  // Store text for copy
  bodyEl.dataset.rawText = text;

  // Show footer
  const footer = document.getElementById(`footer-${msgId}`);
  if (footer) footer.style.display = "flex";

  activeMessage = null;
  thinkingIndicator.style.display = "none";
}

function handleDebateEnd(evt) {
  // Complete final step
  const step = document.getElementById(`step${currentRound}`);
  if (step) { step.classList.remove("active"); step.classList.add("complete"); }
  stepperFill.style.width = "100%";

  thinkingIndicator.style.display = "none";
  verdictBanner.style.display = "block";
  verdictBanner.scrollIntoView({ behavior: "smooth", block: "nearest" });

  resetUI();
}

// ── UI helpers ─────────────────────────────────────────────
function resetUI() {
  isDebating = false;
  startBtn.disabled = false;
  startBtn.querySelector("span:last-child").textContent = "Start Debate";
  setStatus("online", "API Ready");
  checkHealth();
}

function resetDebate() {
  heroSection.style.display = "block";
  arenaSection.style.display = "none";
  clarifierSection.style.display = "none";
  agentsLegend.style.display = "block";
  messagesContainer.innerHTML = "";
  verdictBanner.style.display = "none";
  thinkingIndicator.style.display = "none";
  topicInput.value = "";
  charCount.textContent = "0 / 1000";
  activeMessage = null;
  currentRound = 0;
  resetUI();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function showError(msg) {
  thinkingIndicator.style.display = "none";
  const errEl = document.createElement("div");
  errEl.style.cssText = `
    background: rgba(255,107,107,0.1); border: 1px solid rgba(255,107,107,0.3);
    border-radius: 12px; padding: 20px; color: #ff6b6b;
    font-size: 0.875rem; line-height: 1.6; white-space: pre-wrap;
  `;
  errEl.textContent = "⚠️ " + msg;
  messagesContainer.appendChild(errEl);
  errEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function toggleMessage(msgId) {
  const body = document.getElementById(`body-${msgId}`);
  const btn = document.getElementById(`collapseBtn-${msgId}`);
  if (!body) return;
  const collapsed = body.style.display === "none";
  body.style.display = collapsed ? "" : "none";
  btn?.classList.toggle("collapsed", !collapsed);
}

async function copyMessage(msgId) {
  const body = document.getElementById(`body-${msgId}`);
  const btn = document.getElementById(`copy-${msgId}`);
  if (!body) return;
  const text = body.dataset.rawText || body.innerText;
  try {
    await navigator.clipboard.writeText(text);
    if (btn) {
      btn.classList.add("copied");
      btn.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="m20 6-11 11-5-5"/></svg> Copied!`;
      setTimeout(() => {
        btn.classList.remove("copied");
        btn.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copy`;
      }, 2000);
    }
  } catch {}
}

// ── Simple Markdown Renderer ────────────────────────────────
function renderMarkdown(text) {
  if (!text) return "";
  let html = escHtml(text);

  // Headers ## and ###
  html = html.replace(/^### (.+)$/gm, "<h3>$1</h3>");
  html = html.replace(/^## (.+)$/gm, "<h2>$1</h2>");

  // Bold **text**
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

  // Italic *text*
  html = html.replace(/\*([^*\n]+)\*/g, "<em>$1</em>");

  // Bullet lists
  html = html.replace(/^\* (.+)$/gm, "<li>$1</li>");
  html = html.replace(/^- (.+)$/gm, "<li>$1</li>");
  html = html.replace(/(<li>.*<\/li>\n?)+/g, (m) => `<ul>${m}</ul>`);

  // Numbered lists
  html = html.replace(/^\d+\. (.+)$/gm, "<li>$1</li>");

  // Paragraphs (double newlines)
  html = html
    .split(/\n{2,}/)
    .map(block => {
      block = block.trim();
      if (!block) return "";
      if (/^<(h[123]|ul|ol|li)/.test(block)) return block;
      return `<p>${block.replace(/\n/g, "<br>")}</p>`;
    })
    .filter(Boolean)
    .join("\n");

  return html;
}

function escHtml(str) {
  return (str || "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

// Shake animation (CSS keyframe injected)
const shakeStyle = document.createElement("style");
shakeStyle.textContent = `
  @keyframes shake {
    0%,100%{transform:translateX(0)}
    20%{transform:translateX(-6px)}
    40%{transform:translateX(6px)}
    60%{transform:translateX(-4px)}
    80%{transform:translateX(4px)}
  }
  .shake { animation: shake 0.45s ease; }
`;
document.head.appendChild(shakeStyle);
