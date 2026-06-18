// ── Auth guard ────────────────────────────────────────────────
requireAuth();

// Each conversation gets its own UUID so the backend can store
// them separately. sidebar.js updates this when switching chats.
let currentSessionId = crypto.randomUUID();

// ── DOM refs ─────────────────────────────────────────────────
const chatArea  = document.getElementById('chatArea');
const userInput = document.getElementById('userInput');
const sendBtn   = document.getElementById('sendBtn');

// ── Logout ────────────────────────────────────────────────────
document.getElementById('logoutBtn').addEventListener('click', logout);

// ── Auto-grow textarea ────────────────────────────────────────
userInput.addEventListener('input', () => {
  userInput.style.height = 'auto';
  userInput.style.height = Math.min(userInput.scrollHeight, 140) + 'px';
});

// ── Enter = send (Shift+Enter = newline) ──────────────────────
userInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleSend();
  }
});

sendBtn.addEventListener('click', handleSend);

// ── Core send flow ────────────────────────────────────────────
async function handleSend() {
  const text = userInput.value.trim();
  if (!text) return;

  userInput.value = '';
  userInput.style.height = 'auto';
  setInputDisabled(true);

  const welcome = chatArea.querySelector('.welcome');
  if (welcome) welcome.remove();

  appendMessage('user', text);
  const thinkingRow = appendThinking();
  const stopTimer   = startLiveTimer(thinkingRow);

  try {
    const response = await authFetch(`${API_BASE}/chat`,
  {
    method: 'POST',

    headers: {
      "Content-Type":"application/json",
    },

    body: JSON.stringify({
      message: text,
      session_id:currentSessionId
    }),
  }
);

if (!response.ok) {throw new Error(`HTTP ${response.status}`);}

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let answer = '';
    let progress = [];

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      let boundary;
      while ((boundary = buffer.indexOf('\n\n')) !== -1) {
        const event = buffer.slice(0, boundary).trim();
        buffer = buffer.slice(boundary + 2);

        if (!event.startsWith('data:')) continue;

        try {
          const data = JSON.parse(event.replace(/^data:\s*/, ''));

          if (data.type === 'progress') {
            progress = [{
              step: 1,
              tool: 'assistant',
              summary: data.message,
              duration_ms: 0,
              status: 'running',
            }];
            updateThinkingProgress(thinkingRow, progress);
          }

          if (data.type === 'delta') {
            stopTimer();
            answer += data.delta;
            replaceWithAnswer(thinkingRow, answer, progress);
          }

          if (data.type === 'complete') {
            if (data.progress) progress = data.progress;
            replaceWithAnswer(thinkingRow, answer, progress);
            ConvHistory.addMessage(text, answer);
          }
        } catch (e) {
          console.log('Invalid SSE:', event);
        }
      }
    }

  } catch (err) {
    console.error('Chat error:', err);
    stopTimer();
    replaceWithError(thinkingRow, 'An error occurred. Please try again.');
  } finally {
    setInputDisabled(false);
    userInput.focus();
  }
}

// ── Live timer while waiting ──────────────────────────────────
function startLiveTimer(row) {
  const bubble  = row.querySelector('.msg-bubble');
  const start   = Date.now();

  const interval = setInterval(() => {
    const s = ((Date.now() - start) / 1000).toFixed(1);
    const progText = row.dataset.progress ? ` (${row.dataset.progress})` : '';
    bubble.innerHTML =
      `<span class="thinking-label">Thinking${escapeHtml(progText)}` +
      `<span class="dots"><span></span><span></span><span></span></span></span>` +
      `<span class="thinking-timer">${s}s</span>`;
  }, 100);

  return () => clearInterval(interval);
}

function updateThinkingProgress(row, progress) {
  if (progress && progress[0]) {
    row.dataset.progress = progress[0].summary;
  }
}

// ── Replace thinking bubble with answer + activity panel ─────
function replaceWithAnswer(row, answer, steps) {
  row.classList.remove('thinking');
  const bubble = row.querySelector('.msg-bubble');

  // 1. Answer text (markdown)
  const answerDiv = document.createElement('div');
  answerDiv.className = 'markdown';
  answerDiv.innerHTML = renderMarkdown(answer);
  bubble.innerHTML = '';
  bubble.appendChild(answerDiv);

  // 2. Agent activity panel (only if there are steps)
  if (steps.length > 0) {
    bubble.appendChild(buildActivityPanel(steps));
  }

  scrollToBottom();
}

function replaceWithError(row, message) {
  row.classList.remove('thinking');
  row.classList.add('error');
  row.querySelector('.msg-bubble').textContent = message;
  scrollToBottom();
}

// ── Agent Activity Panel ──────────────────────────────────────
function buildActivityPanel(steps) {
  const totalMs = steps.reduce((sum, s) => sum + (s.duration_ms || 0), 0);

  const panel = document.createElement('div');
  panel.className = 'activity-panel';

  // ── Header (click to toggle) ──
  const header = document.createElement('button');
  header.className = 'activity-header';
  header.innerHTML =
    `<span class="activity-chevron">▶</span>` +
    `<span class="activity-title">Agent Activity</span>` +
    `<span class="activity-meta">${steps.length} step${steps.length !== 1 ? 's' : ''} · ${totalMs}ms</span>`;

  // ── Steps container (collapsed by default) ──
  const body = document.createElement('div');
  body.className = 'activity-body';

  steps.forEach(step => body.appendChild(buildStepRow(step)));

  // Toggle open/close
  header.addEventListener('click', () => {
    const open = panel.classList.toggle('open');
    header.querySelector('.activity-chevron').textContent = open ? '▼' : '▶';
    scrollToBottom();
  });

  panel.appendChild(header);
  panel.appendChild(body);
  return panel;
}

function buildStepRow(step) {
  const statusIcon = step.status === 'completed' ? '✓'
                   : step.status === 'error'     ? '✗'
                   : '⟳';

  const toolLabel = formatToolName(step.tool);

  const row = document.createElement('div');
  row.className = 'activity-step';

  // ── Step header (click to expand arguments) ──
  const stepHeader = document.createElement('button');
  stepHeader.className = 'step-header';
  stepHeader.innerHTML =
    `<span class="step-icon ${step.status}">${statusIcon}</span>` +
    `<span class="step-name">${escapeHtml(toolLabel)}</span>` +
    `<span class="step-summary">${escapeHtml(step.summary || '')}</span>` +
    `<span class="step-duration">${step.duration_ms ?? '—'}ms</span>` +
    `<span class="step-chevron">›</span>`;

  // ── Step detail (arguments) ──
  const detail = document.createElement('div');
  detail.className = 'step-detail';

  const args = step.arguments || {};
  const argRows = Object.entries(args)
    .map(([k, v]) =>
      `<div class="arg-row">` +
      `<span class="arg-key">${escapeHtml(k)}</span>` +
      `<span class="arg-val">${escapeHtml(typeof v === 'object' ? JSON.stringify(v) : String(v))}</span>` +
      `</div>`
    ).join('');

  detail.innerHTML = argRows || '<span class="arg-empty">No arguments</span>';

  stepHeader.addEventListener('click', () => {
    const open = row.classList.toggle('step-open');
    stepHeader.querySelector('.step-chevron').textContent = open ? '∨' : '›';
    scrollToBottom();
  });

  row.appendChild(stepHeader);
  row.appendChild(detail);
  return row;
}

// snake_case → Title Case
function formatToolName(tool) {
  return (tool || 'Unknown Tool')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}

// ── Markdown renderer ─────────────────────────────────────────
function renderMarkdown(text) {
  let html = text;

  html = html
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) =>
    `<pre><code>${code.trim()}</code></pre>`
  );
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/__(.+?)__/g, '<strong>$1</strong>');
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
  html = html.replace(/_([^_]+)_/g, '<em>$1</em>');
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm,  '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm,   '<h1>$1</h1>');

  html = html.replace(/(^[-*] .+\n?)+/gm, match => {
    const items = match.trim().split('\n')
      .map(line => `<li>${line.replace(/^[-*] /, '')}</li>`).join('');
    return `<ul>${items}</ul>`;
  });

  html = html.replace(/(^\d+\. .+\n?)+/gm, match => {
    const items = match.trim().split('\n')
      .map(line => `<li>${line.replace(/^\d+\. /, '')}</li>`).join('');
    return `<ol>${items}</ol>`;
  });

  html = html.replace(/^(---|\*\*\*)$/gm, '<hr>');

  html = html.split(/\n{2,}/).map(block => {
    if (/^<(h[1-3]|ul|ol|pre|hr)/.test(block.trim())) return block;
    return `<p>${block.trim().replace(/\n/g, '<br>')}</p>`;
  }).join('\n');

  return html;
}

// ── Message builders ──────────────────────────────────────────
function appendMessage(role, text) {
  const row = document.createElement('div');
  row.className = `msg-row ${role}`;

  const label = document.createElement('div');
  label.className = `msg-label label-${role === 'user' ? 'user' : 'ai'}`;
  label.textContent = role === 'user' ? 'You' : 'Assistant';

  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';

  if (role === 'user') {
    bubble.textContent = text;
  } else {
    bubble.classList.add('markdown');
    bubble.innerHTML = renderMarkdown(text);
  }

  row.appendChild(label);
  row.appendChild(bubble);
  chatArea.appendChild(row);
  scrollToBottom();
  return row;
}

function appendThinking() {
  const row = document.createElement('div');
  row.className = 'msg-row ai thinking';

  const label = document.createElement('div');
  label.className = 'msg-label label-ai';
  label.textContent = 'Assistant';

  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  bubble.innerHTML =
    `<span class="thinking-label">Thinking` +
    `<span class="dots"><span></span><span></span><span></span></span></span>` +
    `<span class="thinking-timer">0.0s</span>`;

  row.appendChild(label);
  row.appendChild(bubble);
  chatArea.appendChild(row);
  scrollToBottom();
  return row;
}

// ── Utilities ─────────────────────────────────────────────────
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function scrollToBottom() {
  chatArea.scrollTop = chatArea.scrollHeight;
}

function setInputDisabled(disabled) {
  userInput.disabled = disabled;
  sendBtn.disabled   = disabled;
}

function loadConversation(messages) {
  chatArea.innerHTML = '';
  messages.forEach(({ role, text, content }) => appendMessage(role, text ?? content ?? ''));
}
