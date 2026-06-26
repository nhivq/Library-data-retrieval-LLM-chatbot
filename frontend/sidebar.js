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
     deleteConversation(conv.session_id);
  });
  if (conv.session_id === currentSessionId) {
    item.classList.add('active');
  }
  list.appendChild(item);
  });
}

async function deleteConversation(sessionId){

  try{

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

    fetchConversations();

  }
  catch(err){
    console.error(
      "Delete conversation error:",
      err
    );
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
