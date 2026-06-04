// ── Config ───────────────────────────────────────────────────
const API_URL = 'http://localhost:8000/chat';

// ── Auth guard — redirect to login if not authenticated ───────
if (!Auth.isLoggedIn()) {
  window.location.replace('login.html');
}

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

  // Clear & reset input
  userInput.value = '';
  userInput.style.height = 'auto';
  setInputDisabled(true);

  // Remove welcome hint on first message
  const welcome = chatArea.querySelector('.welcome');
  if (welcome) welcome.remove();

  // Append user bubble
  appendMessage('user', text);

  // Append thinking indicator — keep reference to replace it
  const thinkingRow = appendThinking();

  try {
    const response = await fetch(API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text }),
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const data = await response.json();
    const answer = data.answer ?? 'No response received.';
    replaceThinking(thinkingRow, answer, false);

  } catch (err) {
    console.error('Chat error:', err);
    replaceThinking(thinkingRow, 'An error occurred. Please try again.', true);
  } finally {
    setInputDisabled(false);
    userInput.focus();
  }
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
  bubble.textContent = text;

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
  bubble.innerHTML = 'Thinking<span class="dots"><span></span><span></span><span></span></span>';

  row.appendChild(label);
  row.appendChild(bubble);
  chatArea.appendChild(row);
  scrollToBottom();
  return row;
}

function replaceThinking(row, text, isError) {
  row.classList.remove('thinking');
  if (isError) row.classList.add('error');

  const bubble = row.querySelector('.msg-bubble');
  bubble.textContent = text;
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