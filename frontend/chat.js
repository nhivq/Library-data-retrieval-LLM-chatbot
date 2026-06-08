// ── Config ───────────────────────────────────────────────────
const API_URL = "http://localhost:8000/chat";

// ── Auth guard — redirect to login if not authenticated ───────
if (!Auth.isLoggedIn()) {
  window.location.replace("login.html");
}

// ── DOM refs ─────────────────────────────────────────────────
const chatArea = document.getElementById("chatArea");
const userInput = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");

// ── Logout ────────────────────────────────────────────────────
document.getElementById("logoutBtn").addEventListener("click", logout);

// ── Auto-grow textarea ────────────────────────────────────────
userInput.addEventListener("input", () => {
  userInput.style.height = "auto";
  userInput.style.height = Math.min(userInput.scrollHeight, 140) + "px";
});

// ── Enter = send (Shift+Enter = newline) ──────────────────────
userInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    handleSend();
  }
});

sendBtn.addEventListener("click", handleSend);

// ── Core send flow ────────────────────────────────────────────
async function handleSend() {
  const text = userInput.value.trim();
  if (!text) return;

  // Clear & reset input
  userInput.value = "";
  userInput.style.height = "auto";
  setInputDisabled(true);

  // Remove welcome hint on first message
  const welcome = chatArea.querySelector(".welcome");
  if (welcome) welcome.remove();

  // Append user bubble
  appendMessage("user", text);

  // Append thinking indicator — keep reference to replace it
  const thinkingRow = appendThinking();

  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const data = await response.json();
    const answer = data.answer ?? "No response received.";
    replaceThinking(thinkingRow, answer, false, data.progress || []);
  } catch (err) {
    console.error("Chat error:", err);
    replaceThinking(thinkingRow, "An error occurred. Please try again.", true);
  } finally {
    setInputDisabled(false);
    userInput.focus();
  }
}

// ── Message builders ──────────────────────────────────────────
function appendMessage(role, text) {
  const row = document.createElement("div");
  row.className = `msg-row ${role}`;

  const label = document.createElement("div");
  label.className = `msg-label label-${role === "user" ? "user" : "ai"}`;
  label.textContent = role === "user" ? "You" : "Assistant";

  const bubble = document.createElement("div");
  bubble.className = "msg-bubble";
  bubble.innerHTML =
    role === "user" ? escapeHtml(text) : renderMarkdown(text);

  row.appendChild(label);
  row.appendChild(bubble);
  chatArea.appendChild(row);
  scrollToBottom();
  return row;
}

function appendThinking() {
  const row = document.createElement("div");
  row.className = "msg-row ai thinking";

  const label = document.createElement("div");
  label.className = "msg-label label-ai";
  label.textContent = "Assistant";

  const bubble = document.createElement("div");
  bubble.className = "msg-bubble";
  bubble.innerHTML = `
    <div class="progress-header">
      <span>Assembling AI agent</span>
      <span class="dots"><span></span><span></span><span></span></span>
    </div>
    <div class="progress-details">Preparing tools and fetching results...</div>
    <div class="progress-timer">Elapsed: 0s</div>
  `;

  row.appendChild(label);
  row.appendChild(bubble);
  chatArea.appendChild(row);
  scrollToBottom();

  row.elapsedSeconds = 0;
  row.timerInterval = setInterval(() => {
    row.elapsedSeconds += 1;
    const timer = row.querySelector(".progress-timer");
    if (timer) timer.textContent = `Elapsed: ${row.elapsedSeconds}s`;
  }, 1000);

  return row;
}

function replaceThinking(row, text, isError, progress = []) {
  if (row.timerInterval) {
    clearInterval(row.timerInterval);
  }

  row.classList.remove("thinking");
  if (isError) row.classList.add("error");

  const bubble = row.querySelector(".msg-bubble");
  bubble.innerHTML = renderMarkdown(text);

  if (progress && progress.length) {
    const progressHtml = progress
      .map((item) => `<li>${escapeHtml(item)}</li>`)
      .join("");

    bubble.insertAdjacentHTML(
      "beforeend",
      `<div class="progress-summary"><strong>Progress details:</strong><ul>${progressHtml}</ul></div>`
    );
  }

  scrollToBottom();
}

function escapeHtml(value) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderMarkdown(markdown) {
  const escaped = escapeHtml(markdown);

  const bolded = escaped.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  const lines = bolded.split("\n");

  let html = "";
  let inList = false;

  lines.forEach((line) => {
    const trimmed = line.trim();

    if (trimmed.startsWith("- ")) {
      if (!inList) {
        html += "<ul>";
        inList = true;
      }
      html += `<li>${trimmed.slice(2)}</li>`;
    } else {
      if (inList) {
        html += "</ul>";
        inList = false;
      }

      if (trimmed === "") {
        html += "<br>";
      } else {
        html += `<p>${trimmed}</p>`;
      }
    }
  });

  if (inList) html += "</ul>";
  return html;
}

// ── Helpers ───────────────────────────────────────────────────
function scrollToBottom() {
  chatArea.scrollTop = chatArea.scrollHeight;
}

function setInputDisabled(disabled) {
  userInput.disabled = disabled;
  sendBtn.disabled = disabled;
}
