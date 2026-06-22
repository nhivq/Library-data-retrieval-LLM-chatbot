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

const QUICK_ACTIONS = [
  'Find fantasy books',
  'Save all books to bookmark',
  'Search authors',
  'My bookmarks',
  'Find highly rated books'
];

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
async function handleSend(messageOverride = null) {
  const text = (messageOverride ?? userInput.value).trim();
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
      if (done) {
        stopTimer();
        if (answer || progress.length > 0) {
          replaceWithAnswer(thinkingRow, answer, progress);
        }
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
            stopTimer();
            answer += data.delta;
            replaceWithAnswer(thinkingRow, answer, progress);
          }

          if (data.type === 'complete') {
            stopTimer();
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
  html = html.replace(
    /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
  );
  html = html.replace(
    /work_key:\s*\((https?:\/\/[^)\s]+)\)/gi,
    (_, url) => {
      const normalized = url.includes('/works/')
        ? url
        : url.replace(/\/([A-Za-z0-9]+W)(?:\?.*)?$/, '/works/$1');
      return `work_key: (<a href="${normalized}" target="_blank" rel="noopener noreferrer">${normalized}</a>)`;
    }
  );
  html = html.replace(
    /(^|[^"'=])(https?:\/\/[^\s<)]+)/g,
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

<<<<<<< HEAD
function renderAssistantContent(container, text) {
  const parsed = parseBookList(text);

  if (!parsed) {
    const answerDiv = document.createElement('div');
    answerDiv.className = 'markdown';
    answerDiv.innerHTML = renderMarkdown(text);
    container.appendChild(answerDiv);
    return;
  }

  if (parsed.intro) {
    const intro = document.createElement('div');
    intro.className = 'markdown';
    intro.innerHTML = renderMarkdown(parsed.intro);
    container.appendChild(intro);
  }

  const cards = document.createElement('div');
  cards.className = 'book-card-list';

  parsed.books.forEach((book) => {
    cards.appendChild(buildBookCard(book));
  });

  container.appendChild(cards);

  if (parsed.outro) {
    const outro = document.createElement('div');
    outro.className = 'markdown';
    outro.innerHTML = renderMarkdown(parsed.outro);
    container.appendChild(outro);
  }
}

function parseBookList(text) {
  const lines = text.split('\n');
  const books = [];
  let currentBook = null;
  let firstBookIndex = -1;
  let lastBookIndex = -1;

  for (let index = 0; index < lines.length; index += 1) {
    const rawLine = lines[index];
    const line = rawLine.trim();

    const title = extractBookTitle(line);
    if (title) {
      if (currentBook) {
        books.push(normalizeBook(currentBook));
      }

      if (firstBookIndex === -1) {
        firstBookIndex = index;
      }

      currentBook = {
        title,
        authors: '',
        rating: '',
        published: '',
        tags: '',
        work_key: '',
        link: ''
      };
      lastBookIndex = index;
      continue;
    }

    if (!currentBook) {
      continue;
    }

    const fieldMatch = line.match(/^[-*]?\s*(Author|Authors|Rating|Published|Publish Date|Tags|work_key)\s*:\s*(.*)$/i);
    if (fieldMatch) {
      const key = fieldMatch[1].toLowerCase();
      const value = fieldMatch[2].trim();

      if (key === 'author' || key === 'authors') {
        currentBook.authors = value;
      } else if (key === 'rating') {
        currentBook.rating = value;
      } else if (key === 'published' || key === 'publish date') {
        currentBook.published = value;
      } else if (key === 'tags') {
        currentBook.tags = value;
      } else if (key === 'work_key') {
        currentBook.work_key = extractWorkKey(value);
      }

      lastBookIndex = index;
      continue;
    }

    const bookLink = line.match(/^[-*]?\s*\[?View Book\]?\s*:?[\s-]*\(?((?:https?:\/\/)[^)\s]+)\)?$/i)
      || line.match(/^[-*]?\s*\[View Book\]\((https?:\/\/[^)]+)\)$/i);
    if (bookLink) {
      currentBook.link = bookLink[1].trim();
      if (!currentBook.work_key) {
        currentBook.work_key = extractWorkKey(bookLink[1]);
      }
      lastBookIndex = index;
      continue;
    }

    if (!line) {
      continue;
    }

    if (currentBook && !looksLikeAnotherSection(line)) {
      currentBook.title = `${currentBook.title} ${line}`.trim();
      lastBookIndex = index;
      continue;
    }

    break;
  }

  if (currentBook) {
    books.push(normalizeBook(currentBook));
  }

  if (!books.length) {
    return null;
  }

  return {
    intro: lines.slice(0, firstBookIndex).join('\n').trim(),
    books,
    outro: lines.slice(lastBookIndex + 1).join('\n').trim()
  };
}

function normalizeBook(book) {
  return {
    title: book.title || 'Untitled',
    authors: book.authors || 'Unknown author',
    rating: parseRating(book.rating),
    published: book.published || 'Unknown date',
    tags: parseTags(book.tags),
    work_key: book.work_key || '',
    link: book.link || ''
  };
}

function extractBookTitle(line) {
  const cleaned = line
    .replace(/^\d+\.\s+/, '')
    .replace(/^[-*]\s+/, '')
    .replace(/^📖\s*/, '')
    .trim();

  const markdownTitle = cleaned.match(/^\*\*(.+?)\*\*$/);
  if (markdownTitle) {
    return markdownTitle[1].trim();
  }

  const plainTitle = cleaned.match(/^(.+)$/);
  if (!plainTitle) {
    return null;
  }

  const value = plainTitle[1].trim();
  if (!value || /^[A-Za-z_ ]+\s*:/.test(value)) {
    return null;
  }

  return /^\d+\./.test(line) || /^📖/.test(line) ? value : null;
}

function looksLikeAnotherSection(line) {
  return /^#{1,3}\s+/.test(line)
    || /^[-*]\s+/.test(line)
    || /^\d+\.\s+/.test(line)
    || /^[A-Za-z_ ]+\s*:\s*/.test(line);
}

function extractWorkKey(value) {
  const match = value.match(/\/works\/[A-Za-z0-9]+W/);
  return match ? match[0] : value.replace(/[()]/g, '').trim();
}

function parseRating(value) {
  const match = value.match(/\d+(?:\.\d+)?/);
  return match ? Number(match[0]) : null;
}

function parseTags(value) {
  return value
    .split(',')
    .map((tag) => tag.trim())
    .filter(Boolean)
    .slice(0, 6);
}

function buildBookCard(book) {
  const card = document.createElement('section');
  card.className = 'book-card';

  const tagsHtml = book.tags.length
    ? book.tags.map((tag) => `<span class="book-tag">${escapeHtml(tag)}</span>`).join('')
    : '<span class="book-tag muted">No tags</span>';

  card.innerHTML = `
    <div class="book-card-title-row">
      <h3 class="book-card-title">📖 ${escapeHtml(book.title)}</h3>
    </div>
    <div class="book-card-meta">
      <div class="book-card-line">✍️ <span>${escapeHtml(book.authors)}</span></div>
      <div class="book-card-line">${renderRatingVisual(book.rating)}</div>
      <div class="book-card-line">📅 <span>${escapeHtml(book.published)}</span></div>
    </div>
    <div class="book-card-tags">${tagsHtml}</div>
    <div class="book-card-actions">
      <button type="button" class="book-action-btn" data-action="bookmark">🔖 Bookmark</button>
      <button type="button" class="book-action-btn accent" data-action="similar">✨ Find Similar Books</button>
    </div>
  `;

  if (!book.work_key) {
    card.querySelector('[data-action="bookmark"]').disabled = true;
    card.querySelector('[data-action="bookmark"]').title = 'Bookmark requires a work_key in the assistant response';
  }

  if (book.link) {
    const meta = document.createElement('a');
    meta.className = 'book-card-link';
    meta.href = book.link;
    meta.target = '_blank';
    meta.rel = 'noopener noreferrer';
    meta.textContent = 'Open book';
    card.insertBefore(meta, card.querySelector('.book-card-actions'));
  }

  card.querySelector('[data-action="bookmark"]').addEventListener('click', () => saveBookmarkFromCard(book));
  card.querySelector('[data-action="similar"]').addEventListener('click', () => handleSend(`Find similar books to:\n${book.title}`));

  return card;
}

function renderRatingVisual(rating) {
  if (rating === null) {
    return '⭐ <span>Unrated</span>';
  }

  const stars = Math.max(1, Math.min(5, Math.round(rating)));
  const filled = '★'.repeat(stars);
  const empty = '☆'.repeat(5 - stars);
  return `⭐ <span class="book-rating-stars">${filled}${empty}</span> <span class="book-rating-number">${escapeHtml(rating.toFixed(1))}</span>`;
}

async function saveBookmarkFromCard(book) {
  if (!book.work_key) {
    return;
  }

  try {
    const response = await authFetch(`${API_BASE}/bookmarks/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ work_key: book.work_key })
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    if (typeof fetchBookmarks === 'function') {
      fetchBookmarks();
    }
  } catch (error) {
    console.error('Bookmark save error:', error);
  }
}

=======
>>>>>>> parent of f36d86b (frontend similar books pattern added)
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

  messages.forEach(({ role, text, content }) => {

    if (role === 'system') return;

    appendMessage(
      role,
      text ?? content ?? ''
    );

  });
}
