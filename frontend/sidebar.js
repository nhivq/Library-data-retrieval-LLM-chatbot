// ─────────────────────────────────────────────────────────────
// sidebar.js — Conversation History + Bookmarks
// Loaded after auth.js and chat.js in chat.html
// ─────────────────────────────────────────────────────────────

// API_BASE is declared in auth.js (loaded before this file)

// ── Conversation History ──────────────────────────────────────
// Stored in sessionStorage as an array of conversation objects:
// [{ id, label, createdAt, messages: [{role, text}] }, ...]

async function fetchConversations(){

  const res = await authFetch(
    `${API_BASE}/conversations/`
  );

  if(!res.ok){
    console.error(
      "Failed loading conversations"
    );
    return;
  }

  const data = await res.json();


  renderBackendConversations(data);
}

function formatSessionLabel(index) {
  return `Conversation ${index + 1}`;
}

function formatConversationLabel(conv, index) {

  // Use the first user message as the conversation title.
  // If the chat has no user message yet, keep the old generic label.
  const firstMessage = (conv.first_message || '').trim();

  if(!firstMessage){
    return formatSessionLabel(index);
  }

  return firstMessage.length > 42
    ? `${firstMessage.slice(0, 42)}…`
    : firstMessage;
}

function shortSessionId(sessionId) {
  return sessionId.length > 12 ? `${sessionId.slice(0, 8)}…${sessionId.slice(-4)}` : sessionId;
}

const ConvHistory = {

  addMessage(userText, aiText) {
    // Backend already saved it.
    // Just refresh sidebar.
    setTimeout(
        fetchConversations,
        300
    );

  },

  newConversation() {

    const sessionId = crypto.randomUUID();

    currentSessionId = sessionId;

    loadConversation([]);

  },

  switchTo(sessionId) {

    currentSessionId = sessionId;

    loadConversationFromBackend(sessionId);
  }
};

// ── Render Conversation List ──────────────────────────────────
function renderBackendConversations(convs){

 const list = document.getElementById("convList");

 list.innerHTML="";


  convs.forEach((conv, index)=>{

  const item = document.createElement("div");

  item.className="conv-item";

  item.innerHTML=`
  <span class="conv-item-text">
    <span class="conv-item-label">${escapeHtml(formatConversationLabel(conv, index))}</span>
    <span class="conv-item-time">${escapeHtml(shortSessionId(conv.session_id))}</span>
  </span>
  <button class="conv-delete" title="Delete conversation">×</button>
  `;
  item.onclick=()=>{
     currentSessionId = conv.session_id;
     loadConversationFromBackend(conv.session_id);
  };
  item.querySelector('.conv-delete').addEventListener('click', (event) => {
     event.stopPropagation();
     deleteConversation(conv.session_id, item);
  });
  if (conv.session_id === currentSessionId) {
    item.classList.add('active');
  }
  list.appendChild(item);
  });
}

async function deleteConversation(sessionId, item = null){

  try{
    if (item) {
      item.remove();
    }

    const res = await authFetch(
      `${API_BASE}/conversations/${sessionId}`,
      {
        method: 'DELETE'
      }
    );

    if(!res.ok)
      throw new Error(`HTTP ${res.status}`);

    if(sessionId === currentSessionId){
      ConvHistory.newConversation();
      showWelcome();
    }

  }
  catch(err){
    console.error(
      "Delete conversation error:",
      err
    );
    fetchConversations();
  }
}

async function clearConversations(){
  const list = document.getElementById("convList");
  const button = document.getElementById("clearConversationsBtn");

  if (button) {
    button.disabled = true;
    button.textContent = "Clearing";
  }

  list.innerHTML = '<p class="sidebar-empty">No conversations yet.</p>';
  ConvHistory.newConversation();
  showWelcome();

  try {
    const res = await authFetch(
      `${API_BASE}/conversations/`,
      {
        method: 'DELETE'
      }
    );

    if(!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
  } catch(err) {
    console.error(
      "Clear conversations error:",
      err
    );
    fetchConversations();
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = "Clear";
    }
  }
}

// ── Loading conversation ──────────────────────────────────────
async function loadConversationFromBackend(sessionId){

 try {

    const res = await authFetch(
      `${API_BASE}/conversations/${sessionId}`
    );

    if(!res.ok)
        throw new Error("Conversation load failed");

    const messages = await res.json();

    loadConversation(messages);

 }
 catch(err){
    console.error(err);
 }
}

// ── New Chat button ───────────────────────────────────────────
document.getElementById('newChatBtn').addEventListener('click', () => {
  ConvHistory.newConversation();

  showWelcome();
});

document.getElementById('clearConversationsBtn').addEventListener('click', clearConversations);

// ── Bookmarks ─────────────────────────────────────────────────
async function fetchBookmarks() {
  const list = document.getElementById('bookmarkList');

  list.innerHTML = '<p class="sidebar-empty">Loading…</p>';

  try {
    const res = await authFetch(`${API_BASE}/bookmarks`);
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

    const link = document.createElement('a');
    link.className = 'bookmark-link';
    link.href = normalizeBookmarkWorkUrl(bm.work_key || '');
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.title = bm.title || 'Open book on OpenLibrary';

    const cover = document.createElement('div');
    cover.className = 'bookmark-cover';

    if (bm.cover_id) {
      const image = document.createElement('img');
      image.src = `https://covers.openlibrary.org/b/id/${bm.cover_id}-M.jpg`;
      image.alt = bm.title || 'Book cover';
      image.loading = 'lazy';
      image.addEventListener('error', () => {
        cover.replaceChildren(buildBookmarkFallback(bm));
      });
      cover.appendChild(image);
    } else {
      cover.appendChild(buildBookmarkFallback(bm));
    }

    const title = document.createElement('span');
    title.className = 'bookmark-title';
    title.textContent = bm.title || 'Untitled';

    const removeButton = document.createElement('button');
    removeButton.className = 'bookmark-remove';
    removeButton.type = 'button';
    removeButton.textContent = 'Remove';
    removeButton.addEventListener('click', () => removeBookmark(bm));

    link.appendChild(cover);
    link.appendChild(title);
    item.appendChild(link);
    item.appendChild(removeButton);
    list.appendChild(item);
  });
}

function normalizeBookmarkWorkUrl(value) {
  const match = String(value).match(/\/works\/OL\d+[A-Z]\b|\bOL\d+[A-Z]\b/i);

  if (!match) {
    return 'https://openlibrary.org';
  }

  const workKey = match[0].startsWith('/works/')
    ? match[0]
    : `/works/${match[0]}`;

  return `https://openlibrary.org${workKey}`;
}

function buildBookmarkFallback(bookmark) {
  const fallback = document.createElement('div');
  fallback.className = 'bookmark-cover-fallback';
  fallback.textContent = truncateText(bookmark.title || 'Untitled', 54);
  return fallback;
}

function truncateText(value, maxLength) {
  const text = String(value || '').trim();

  if (text.length <= maxLength) {
    return text;
  }

  return `${text.slice(0, maxLength - 3).trim()}...`;
}

async function removeBookmark(bm) {

  try {
    const res = await authFetch(`${API_BASE}/bookmarks/${bm.id || bm.work_key}`, {
      method: 'DELETE'
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
// ── Init ──────────────────────────────────────────────
setTimeout(() => {
    fetchConversations();
    fetchBookmarks();
}, 0);
