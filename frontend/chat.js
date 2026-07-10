// ── Auth guard ────────────────────────────────────────────────
requireAuth();

// Each conversation gets its own UUID so the backend can store
// them separately. sidebar.js updates this when switching chats.
let currentSessionId = crypto.randomUUID();

// ── DOM refs ─────────────────────────────────────────────────
const chatArea  = document.getElementById('chatArea');
const userInput = document.getElementById('userInput');
const sendBtn   = document.getElementById('sendBtn');
const quickActionsList = document.getElementById('quickActionsList');
const chatColumn = document.querySelector('.chat-column');

const QUICK_ACTIONS = [
  'Find fantasy books',
  'Save all books to bookmark',
  'Search authors',
  'My bookmarks',
  'Find highly rated books',
  'Recommend similar books'
];

const bookDetailsCache = new Map();
const bookDetailsRequests = new Map();

if (quickActionsList) {
  QUICK_ACTIONS.forEach((prompt) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'quick-action-btn';
    button.textContent = prompt;
    button.addEventListener('click', () => handleSend(prompt));
    quickActionsList.appendChild(button);
  });
}

setWelcomeMode(true);

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

sendBtn.addEventListener('click', () => handleSend());

// ── Core send flow ────────────────────────────────────────────
async function handleSend(messageOverride = null) {
  const text = (messageOverride ?? userInput.value).trim();
  if (!text) return;

  userInput.value = '';
  userInput.style.height = 'auto';
  setInputDisabled(true);

  const welcome = chatArea.querySelector('.welcome');
  if (welcome) welcome.remove();

  setWelcomeMode(false);

  appendMessage('user', text);
  if (typeof ConvHistory !== 'undefined' && ConvHistory.addUserMessage) {
    ConvHistory.addUserMessage(text);
  }
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
    let finalRendered = false;

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        if (!finalRendered && (answer || progress.length > 0)) {
          await replaceWithAnswer(thinkingRow, answer, progress);
        }
        stopTimer();
        console.log("stream finished");
        break;
      }

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
            answer += data.delta;
            stopTimer();
            renderStreamingAnswer(thinkingRow, answer, progress);
          }

          if (data.type === 'complete') {
            if (data.progress) progress = data.progress;
            updateThinkingProgress(thinkingRow, [{
              summary: 'Formatting book cards',
            }]);
            await replaceWithAnswer(thinkingRow, answer, progress);
            stopTimer();
            finalRendered = true;
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

function renderStreamingAnswer(row, answer, steps) {
  row.classList.remove('thinking');
  const bubble = row.querySelector('.msg-bubble');

  const answerDiv = document.createElement('div');
  answerDiv.className = 'markdown';
  answerDiv.innerHTML = renderMarkdown(answer);

  bubble.innerHTML = '';
  bubble.appendChild(answerDiv);

  if (steps.length > 0) {
    bubble.appendChild(buildActivityPanel(steps));
  }

  scrollToBottom();
}

// ── Replace thinking bubble with answer + activity panel ─────
async function replaceWithAnswer(row, answer, steps) {
  const answerDiv = document.createElement('div');
  answerDiv.className = 'markdown';
  answerDiv.innerHTML = renderMarkdown(answer);
  await enhanceBookLinks(answerDiv);

  row.classList.remove('thinking');
  const bubble = row.querySelector('.msg-bubble');

  bubble.innerHTML = '';
  bubble.appendChild(answerDiv);

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
  html = html.replace(
    /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
  );
  html = html.replace(
    /work_key:\s*(\/works\/OL\d+[A-Z]\b|\bOL\d+[A-Z]\b)/gi,
    (_, workKey) => {
      const normalized = normalizeOpenLibraryWorkUrl(workKey);
      return `work_key: <a href="${normalized}" target="_blank" rel="noopener noreferrer">${normalized}</a>`;
    }
  );
  html = html.replace(
    /work_key:\s*\((https?:\/\/[^)\s]+)\)/gi,
    (_, url) => {
      const normalized = normalizeOpenLibraryWorkUrl(url);
      return `work_key: (<a href="${normalized}" target="_blank" rel="noopener noreferrer">${normalized}</a>)`;
    }
  );
  html = html.replace(
    /(^|[^"'=>])(https?:\/\/[^\s<)]+)/g,
    (_, prefix, url) => `${prefix}<a href="${url}" target="_blank" rel="noopener noreferrer">${url}</a>`
  );
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm,  '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm,   '<h1>$1</h1>');

  html = html.replace(/(^[-*] .+\n?)+/gm, match => {
    const items = match.trim().split('\n')
      .map(line => `<li>${line.replace(/^[-*] /, '')}</li>`).join('');
    return `<ul>${items}</ul>`;
  });

  html = html.replace(/^(---|\*\*\*)$/gm, '<hr>');

  const lines = html.split('\n');
  const out = [];
  let paragraph = [];
  let ordered = [];
  let unordered = [];

  const flushParagraph = () => {
    if (paragraph.length) {
      out.push(`<p>${paragraph.join('<br>')}</p>`);
      paragraph = [];
    }
  };

  const flushOrdered = () => {
    if (ordered.length) {
      out.push(`<ol>${ordered.map(item => `<li>${item}</li>`).join('')}</ol>`);
      ordered = [];
    }
  };

  const flushUnordered = () => {
    if (unordered.length) {
      out.push(`<ul>${unordered.map(item => `<li>${item}</li>`).join('')}</ul>`);
      unordered = [];
    }
  };

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    if (!line.trim()) {
      flushParagraph();
      flushUnordered();
      continue;
    }

    const orderedMatch = line.match(/^(\d+)\.\s+(.*)$/);
    if (orderedMatch) {
      flushParagraph();
      flushUnordered();
      ordered.push(orderedMatch[2]);
      continue;
    }

    const unorderedMatch = line.match(/^[-*]\s+(.*)$/);
    if (unorderedMatch) {
      flushParagraph();
      flushOrdered();
      unordered.push(unorderedMatch[1]);
      continue;
    }

    if (ordered.length) {
      if (line.startsWith('- ') || line.startsWith('* ')) {
        ordered[ordered.length - 1] += `<br>${line}`;
        continue;
      }
      ordered[ordered.length - 1] += `<br>${line}`;
      continue;
    }

    if (unordered.length) {
      unordered[unordered.length - 1] += `<br>${line}`;
      continue;
    }

    paragraph.push(line);
  }

  flushParagraph();
  flushOrdered();
  flushUnordered();

  html = out.join('\n');

  return html;
}

function normalizeOpenLibraryWorkUrl(value) {

  // Accept either the raw database key or an OpenLibrary URL,
  // then render a real link instead of a placeholder.
  const workKeyMatch = String(value).match(
    /\/works\/OL\d+[A-Z]\b|\bOL\d+[A-Z]\b/i
  );

  if(!workKeyMatch){
    return value;
  }

  const workKey = workKeyMatch[0].startsWith('/works/')
    ? workKeyMatch[0]
    : `/works/${workKeyMatch[0]}`;

  return `https://openlibrary.org${workKey}`;
}

function getWorkKeyFromOpenLibraryUrl(value) {
  const match = String(value).match(/\/works\/OL\d+[A-Z]\b/i);
  return match ? match[0] : null;
}

function getCoverUrl(coverId) {
  return `https://covers.openlibrary.org/b/id/${coverId}-M.jpg`;
}

async function enhanceBookLinks(container) {
  const anchors = [...container.querySelectorAll('a[href*="openlibrary.org/works/"]')];
  const seen = new Set();
  const tasks = [];

  for (const anchor of anchors) {
    const workKey = getWorkKeyFromOpenLibraryUrl(anchor.href);

    if (!workKey || seen.has(workKey)) {
      continue;
    }

    seen.add(workKey);

    tasks.push(
      fetchBookDetails(workKey)
        .then((book) => {
          if (!book) {
            return;
          }

          const card = buildBookResultCard(book);
          const host = anchor.closest('li, p') || anchor;

          if (host.querySelector && host.querySelector('.book-result-card')) {
            return;
          }

          replaceBookResult(host, card);
        })
        .catch((error) => {
          console.log('Could not load book cover:', workKey, error);
        })
    );
  }

  if (tasks.length) {
    await Promise.allSettled(tasks);
    scrollToBottom();
  }
}

async function fetchBookDetails(workKey) {
  if (bookDetailsCache.has(workKey)) {
    return bookDetailsCache.get(workKey);
  }

  if (bookDetailsRequests.has(workKey)) {
    return bookDetailsRequests.get(workKey);
  }

  const request = authFetch(`${API_BASE}/books${workKey}`)
    .then(async (response) => {
      if (!response.ok) {
        return null;
      }

      const book = await response.json();
      bookDetailsCache.set(workKey, book);
      return book;
    })
    .finally(() => {
      bookDetailsRequests.delete(workKey);
    });

  bookDetailsRequests.set(workKey, request);

  return request;
}

function replaceBookResult(host, card) {
  host.replaceChildren(card);
  host.classList.add('book-result-item');
}

function buildBookResultCard(book) {
  const card = document.createElement('div');
  card.className = 'book-result-card';

  card.appendChild(buildBookCoverCard(book));
  card.appendChild(buildBookDetails(book));

  return card;
}

function buildBookCoverCard(book) {
  const card = document.createElement('div');
  card.className = 'book-cover-card';

  const cover = document.createElement('div');
  cover.className = 'book-cover-frame';

  if (book.cover_id) {
    const image = document.createElement('img');
    image.className = 'book-cover-img';
    image.src = getCoverUrl(book.cover_id);
    image.alt = book.title || 'Book cover';
    image.loading = 'lazy';
    image.addEventListener('error', () => {
      cover.replaceChildren(buildBookCoverFallback(book));
    });
    cover.appendChild(image);
  } else {
    cover.appendChild(buildBookCoverFallback(book));
  }

  card.appendChild(cover);
  return card;
}

function buildBookDetails(book) {
  const details = document.createElement('div');
  details.className = 'book-result-details';

  const title = document.createElement('a');
  title.className = 'book-result-title';
  title.href = normalizeOpenLibraryWorkUrl(book.work_key || '');
  title.target = '_blank';
  title.rel = 'noopener noreferrer';
  title.textContent = book.title || 'Untitled book';

  details.appendChild(title);
  details.appendChild(buildBookMetaRow('Author', formatAuthors(book.authors)));
  details.appendChild(buildBookMetaRow('Rating', formatRating(book.rating)));
  details.appendChild(buildBookMetaRow('Published', formatDate(book.publish_date)));
  details.appendChild(buildBookTags(book.tags || []));
  details.appendChild(buildBookActions(book));

  return details;
}

function buildBookMetaRow(label, value) {
  const row = document.createElement('div');
  row.className = 'book-meta-row';

  const labelSpan = document.createElement('span');
  labelSpan.className = 'book-meta-label';
  labelSpan.textContent = label;

  const valueSpan = document.createElement('span');
  valueSpan.className = 'book-meta-value';
  valueSpan.textContent = value || 'Unavailable';

  row.appendChild(labelSpan);
  row.appendChild(valueSpan);

  return row;
}

function buildBookTags(tags) {
  const row = document.createElement('div');
  row.className = 'book-tag-row';

  tags.slice(0, 4).forEach((tag) => {
    const pill = document.createElement('button');
    pill.type = 'button';
    pill.className = 'book-tag-pill';
    pill.textContent = tag;
    pill.title = `Find highly rated ${tag} books`;
    pill.addEventListener('click', () => showTopRatedBooksByTag(tag));
    row.appendChild(pill);
  });

  return row;
}

async function showTopRatedBooksByTag(tag) {
  appendMessage('user', `Show highly rated books tagged "${tag}"`);

  const thinkingRow = appendThinking();
  const stopTimer = startLiveTimer(thinkingRow);

  try {
    const response = await authFetch(
      `${API_BASE}/books/top-rated-by-tag?tag=${encodeURIComponent(tag)}&limit=5`
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const books = await response.json();

    stopTimer();
    await replaceWithTagResults(thinkingRow, tag, books);

  } catch (error) {
    console.log('Could not load books by tag:', error);
    stopTimer();
    replaceWithError(thinkingRow, 'Could not load books with this tag.');
  }
}

async function replaceWithTagResults(row, tag, books) {
  row.classList.remove('thinking');

  const bubble = row.querySelector('.msg-bubble');
  bubble.innerHTML = '';

  const header = document.createElement('div');
  header.className = 'markdown';

  if (!books.length) {
    header.textContent = `Sorry, there aren't any books with the same tag: ${tag}.`;
    bubble.appendChild(header);
    scrollToBottom();
    return;
  }

  header.textContent = `Here are the 5 most highly rated books tagged "${tag}".`;
  bubble.appendChild(header);

  books.forEach((book) => {
    bubble.appendChild(buildBookResultCard(book));
  });

  scrollToBottom();
}

function buildBookActions(book) {
  const actions = document.createElement('div');
  actions.className = 'book-actions';

  const bookmark = document.createElement('button');
  bookmark.type = 'button';
  bookmark.className = 'book-action-btn';
  bookmark.textContent = 'Bookmark';
  bookmark.addEventListener('click', () => saveBookCardBookmark(book, bookmark));

  const similar = document.createElement('button');
  similar.type = 'button';
  similar.className = 'book-action-btn';
  similar.textContent = 'Find Similar Books';
  similar.addEventListener('click', () => {
    handleSend(`Find books similar to ${book.title} with work_key: ${book.work_key}`);
  });

  actions.appendChild(bookmark);
  actions.appendChild(similar);

  return actions;
}

async function saveBookCardBookmark(book, button) {
  const originalText = button.textContent;

  button.disabled = true;
  button.textContent = 'Saving...';

  try {
    const response = await authFetch(`${API_BASE}/bookmarks/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        work_key: book.work_key,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    button.textContent = 'Bookmarked';

    if (typeof fetchBookmarks === 'function') {
      fetchBookmarks();
    }
  } catch (error) {
    console.log('Could not save bookmark:', error);
    button.disabled = false;
    button.textContent = originalText;
  }
}

function buildBookCoverFallback(book) {
  const fallback = document.createElement('div');
  fallback.className = 'book-cover-fallback';

  const title = document.createElement('div');
  title.className = 'book-cover-title';
  title.textContent = truncateText(book.title || 'Untitled book', 72);

  const authors = document.createElement('div');
  authors.className = 'book-cover-authors';
  authors.textContent = truncateText((book.authors || []).join(', '), 44);

  fallback.appendChild(title);

  if (authors.textContent) {
    fallback.appendChild(authors);
  }

  return fallback;
}

function truncateText(value, maxLength) {
  const text = String(value || '').trim();

  if (text.length <= maxLength) {
    return text;
  }

  return `${text.slice(0, maxLength - 3).trim()}...`;
}

function formatAuthors(authors) {
  if (!authors || !authors.length) {
    return null;
  }

  return authors.slice(0, 3).join(', ');
}

function formatRating(rating) {
  if (rating === null || rating === undefined) {
    return null;
  }

  return Number(rating).toFixed(1);
}

function formatDate(value) {
  if (!value) {
    return null;
  }

  const date = new Date(`${value}T00:00:00`);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleDateString(
    undefined,
    {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    }
  );
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
    enhanceBookLinks(bubble);
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

  if(!messages.length){
    showWelcome();
    return;
  }

  setWelcomeMode(false);

  messages.forEach(({ role, text, content }) => {

    if (role === 'system') return;

    appendMessage(
      role,
      text ?? content ?? ''
    );

  });
}

function showWelcome() {

  // Empty chats use a centered welcome screen instead of the normal message list.
  chatArea.innerHTML =
    '<div class="welcome">' +
      '<p class="welcome-hint">How can I help you explore OpenLibrary?</p>' +
      '<p class="welcome-subtitle">Search by author, genre, rating, bookmarks, or similar books.</p>' +
    '</div>';

  setWelcomeMode(true);
}

function setWelcomeMode(enabled) {

  // The CSS uses this class to move the input bar to the middle
  // only when there are no messages in the current conversation.
  chatColumn.classList.toggle(
    'welcome-mode',
    enabled
  );
}
