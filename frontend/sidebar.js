// ─────────────────────────────────────────────────────────────
// sidebar.js — Conversation History + Bookmarks
// Loaded after auth.js and chat.js in chat.html
// ─────────────────────────────────────────────────────────────

// API_BASE is declared in auth.js (loaded before this file)

// ── Conversation History ──────────────────────────────────────
// Stored in sessionStorage as an array of conversation objects:
// [{ id, label, createdAt, messages: [{role, text}] }, ...]

const ConvHistory = {

  _key: 'conversations',

  load() {
    try {
      return JSON.parse(sessionStorage.getItem(this._key)) || [];
    } catch { return []; }
  },

  save(convs) {
    sessionStorage.setItem(this._key, JSON.stringify(convs));
  },

  // Called by chat.js after each assistant reply
  addMessage(userText, aiText) {
    const convs = this.load();

    // Always append to the active conversation
    let active = convs.find(c => c.active);

    if (!active) {
      // Start a new conversation automatically
      active = this._createNew(convs);
    }

    active.messages.push({ role: 'user', text: userText });
    active.messages.push({ role: 'ai',   text: aiText  });

    // Use first user message as label (truncated)
    if (active.messages.filter(m => m.role === 'user').length === 1) {
      active.label = userText.length > 36
        ? userText.slice(0, 36) + '…'
        : userText;
    }

    this.save(convs);
    renderConvList();
  },

  newConversation() {
    const convs = this.load();
    const entry = this._createNew(convs);
    this.save(convs);
    renderConvList();
    currentSessionId = entry.sessionId; // switch chat.js to the new session
  },

  switchTo(id) {
    const convs = this.load();
    convs.forEach(c => c.active = (c.id === id));
    this.save(convs);
    renderConvList();

    const target = convs.find(c => c.id === id);
    if (target) {
      currentSessionId = target.sessionId; // tell chat.js which session to use
      loadConversation(target.messages);
    }
  },

  _createNew(convs) {
    convs.forEach(c => c.active = false);
    const sessionId = crypto.randomUUID();
    const entry = {
      id: sessionId,          // reuse UUID as both the list key and backend session_id
      sessionId,
      label: 'New conversation',
      createdAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      messages: [],
      active: true,
    };
    convs.unshift(entry); // newest first
    return entry;
  },

};

// ── Render Conversation List ──────────────────────────────────
function renderConvList() {
  const list  = document.getElementById('convList');
  const convs = ConvHistory.load();

  if (!convs.length) {
    list.innerHTML = '<p class="sidebar-empty">No conversations yet.</p>';
    return;
  }

  list.innerHTML = '';
  convs.forEach(conv => {
    const item = document.createElement('div');
    item.className = 'conv-item' + (conv.active ? ' active' : '');
    item.innerHTML = `
      <span class="conv-item-label">${escapeHtml(conv.label)}</span>
      <span class="conv-item-time">${conv.createdAt}</span>
    `;
    item.addEventListener('click', () => ConvHistory.switchTo(conv.id));
    list.appendChild(item);
  });
}

// ── New Chat button ───────────────────────────────────────────
document.getElementById('newChatBtn').addEventListener('click', () => {
  ConvHistory.newConversation();

  // Clear the chat area and show welcome hint
  const chatArea = document.getElementById('chatArea');
  chatArea.innerHTML = '<div class="welcome"><p class="welcome-hint">Ask me anything about books —<br>by genre, rating, author, or theme.</p></div>';
});

// ── Bookmarks ─────────────────────────────────────────────────
async function fetchBookmarks() {
  const list = document.getElementById('bookmarkList');

  list.innerHTML = '<p class="sidebar-empty">Loading…</p>';

  try {
    const res = await fetch(`${API_BASE}/bookmarks`, {
      headers: {
        "Authorization": "Bearer " + localStorage.getItem("token")
      }
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();

    // Accept { bookmarks: [...] } or plain array
    const bookmarks = Array.isArray(data) ? data : (data.bookmarks || []);

    renderBookmarks(bookmarks);
  } catch (err) {
    console.error('Bookmarks error:', err);
    list.innerHTML = '<p class="sidebar-empty">Could not load bookmarks.</p>';
  }
}

function renderBookmarks(bookmarks) {
  const list = document.getElementById('bookmarkList');

  if (!bookmarks.length) {
    list.innerHTML = '<p class="sidebar-empty">No bookmarks yet.</p>';
    return;
  }

  list.innerHTML = '';
  bookmarks.forEach(bm => {
    const item = document.createElement('div');
    item.className = 'bookmark-item';
    item.innerHTML = `
      <span class="bookmark-title">${escapeHtml(bm.title || 'Untitled')}</span>
      <span class="bookmark-key">${escapeHtml(bm.work_key || '')}</span>
      <button class="bookmark-remove" data-id="${escapeHtml(String(bm.id || bm.work_key))}">Remove</button>
    `;
    item.querySelector('.bookmark-remove').addEventListener('click', () => removeBookmark(bm));
    list.appendChild(item);
  });
}

async function removeBookmark(bm) {
  const userId = Auth.get();
  if (!userId) return;

  try {
    const res = await fetch(`${API_BASE}/bookmarks/${bm.id || bm.work_key}`, {
      method: 'DELETE',
      headers: {
        "Authorization": "Bearer " + localStorage.getItem("token")
      }
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    fetchBookmarks(); // refresh list
  } catch (err) {
    console.error('Remove bookmark error:', err);
  }
}

// ── Refresh button ────────────────────────────────────────────
document.getElementById('refreshBookmarks').addEventListener('click', fetchBookmarks);

// ── Utility ───────────────────────────────────────────────────
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Init ──────────────────────────────────────────────────────
// Sync currentSessionId with the active conversation on load,
// or seed the first conversation entry with the UUID chat.js already generated.
// setTimeout 0 ensures chat.js has fully run before we reference currentSessionId.
setTimeout(function initSession() {
  const convs = ConvHistory.load();
  const active = convs.find(c => c.active);
  if (active) {
    currentSessionId = active.sessionId;
  } else {
    // First ever load — register the UUID chat.js created as the first conversation
    const entry = ConvHistory._createNew(convs);
    entry.sessionId = currentSessionId; // currentSessionId was set by chat.js on load
    entry.id = currentSessionId;
    ConvHistory.save(convs);
  }
}, 0);

renderConvList();
fetchBookmarks();