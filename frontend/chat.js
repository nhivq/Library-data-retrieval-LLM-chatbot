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

  // Remove welcome hint on first message
  const welcome = chatArea.querySelector('.welcome');
  if (welcome) welcome.remove();

  appendMessage('user', text);
  const thinkingRow = appendThinking();
  const stopTimer = startProgressTimer(thinkingRow);

  try {
    const response = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: text,
        session_id: currentSessionId,
      }),
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const data = await response.json();
    const answer   = data.answer   ?? 'No response received.';
    const progress = data.progress ?? [];

    // Stop timer, flash through the real progress steps, then show answer
    await stopTimer(progress);
    replaceThinking(thinkingRow, answer, false);

    // Save this exchange to conversation history
    ConvHistory.addMessage(text, answer);

  } catch (err) {
    console.error('Chat error:', err);
    replaceThinking(thinkingRow, 'An error occurred. Please try again.', true);
  } finally {
    setInputDisabled(false);
    userInput.focus();
  }
}

// ── Markdown renderer (no external library) ──────────────────
function renderMarkdown(text) {
  let html = text;

  // Escape raw HTML to prevent injection
  html = html
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Code blocks (``` ... ```)
  html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) =>
    `<pre><code>${code.trim()}</code></pre>`
  );

  // Inline code (`code`)
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Bold (**text** or __text__)
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/__(.+?)__/g, '<strong>$1</strong>');

  // Italic (*text* or _text_)
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
  html = html.replace(/_([^_]+)_/g, '<em>$1</em>');

  // Headers (### ## #)
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm,  '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm,   '<h1>$1</h1>');

  // Unordered lists (- item or * item)
  html = html.replace(/(^[-*] .+\n?)+/gm, match => {
    const items = match.trim().split('\n')
      .map(line => `<li>${line.replace(/^[-*] /, '')}</li>`)
      .join('');
    return `<ul>${items}</ul>`;
  });

  // Ordered lists (1. item)
  html = html.replace(/(^\d+\. .+\n?)+/gm, match => {
    const items = match.trim().split('\n')
      .map(line => `<li>${line.replace(/^\d+\. /, '')}</li>`)
      .join('');
    return `<ol>${items}</ol>`;
  });

  // Horizontal rule (--- or ***)
  html = html.replace(/^(---|\*\*\*)$/gm, '<hr>');

  // Paragraphs — wrap double-newline separated blocks
  html = html
    .split(/\n{2,}/)
    .map(block => {
      // Don't wrap blocks that are already HTML tags
      if (/^<(h[1-3]|ul|ol|pre|hr)/.test(block.trim())) return block;
      return `<p>${block.trim().replace(/\n/g, '<br>')}</p>`;
    })
    .join('\n');

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
    // User messages: plain text (safe, no parsing needed)
    bubble.textContent = text;
  } else {
    // AI messages: render markdown
    bubble.classList.add('markdown');
    bubble.innerHTML = renderMarkdown(text);
  }

  row.appendChild(label);
  row.appendChild(bubble);
  chatArea.appendChild(row);
  scrollToBottom();
  return row;
}

// ── Live elapsed timer while waiting for backend ─────────────
// Returns a stop function — call stop(steps) once response arrives
// to swap the timer out for the real progress steps briefly,
// then chat.js calls replaceThinking with the final answer.
function startProgressTimer(row) {
  const bubble = row.querySelector('.msg-bubble');
  const start  = Date.now();

  const interval = setInterval(() => {
    const elapsed = ((Date.now() - start) / 1000).toFixed(1);
    bubble.innerHTML =
      `<span class="progress-step">Thinking… ${elapsed}s</span>` +
      `<span class="dots"><span></span><span></span><span></span></span>`;
  }, 100);

  // Returns a promise that shows each step for 600ms then resolves
  return function stop(steps) {
    clearInterval(interval);
    return new Promise(resolve => {
      if (!steps || steps.length === 0) { resolve(); return; }
      let i = 0;
      function showNext() {
        if (i >= steps.length) { resolve(); return; }
        bubble.innerHTML =
          `<span class="progress-step">${escapeHtml(steps[i])}</span>` +
          `<span class="dots"><span></span><span></span><span></span></span>`;
        i++;
        setTimeout(showNext, 600);
      }
      showNext();
    });
  };
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function appendThinking() {
  const row = document.createElement('div');
  row.className = 'msg-row ai thinking';

  const label = document.createElement('div');
  label.className = 'msg-label label-ai';
  label.textContent = 'Assistant';

  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  bubble.innerHTML = 'Thinking<span class="dots"><span></span><span></span><span></span></span>';

  row.appendChild(label);
  row.appendChild(bubble);
  chatArea.appendChild(row);
  scrollToBottom();
  return row;
}

function replaceThinking(row, text, isError) {
  row.classList.remove('thinking');
  const bubble = row.querySelector('.msg-bubble');
  if (isError) {
    row.classList.add('error');
    bubble.textContent = text;
  } else {
    bubble.classList.add('markdown');
    bubble.innerHTML = renderMarkdown(text);
  }
  scrollToBottom();
}

// ── Helpers ───────────────────────────────────────────────────
function scrollToBottom() {
  chatArea.scrollTop = chatArea.scrollHeight;
}

function setInputDisabled(disabled) {
  userInput.disabled = disabled;
  sendBtn.disabled   = disabled;
}

// ── Load a saved conversation into the chat area ──────────────
function loadConversation(messages) {
  // Clear current chat
  chatArea.innerHTML = '';
  messages.forEach(({ role, text }) => appendMessage(role, text));
}