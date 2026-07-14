import { useEffect, useMemo, useRef, useState } from 'react';
import { API_BASE, authFetch, getCurrentUser } from '../api/client.js';
import BookCard from '../components/BookCard.jsx';
import TopBar from '../components/TopBar.jsx';
import {
  getCoverUrl,
  getWorkKeyFromOpenLibraryUrl,
  normalizeOpenLibraryWorkUrl,
  renderMarkdown,
  truncateText,
} from '../utils.js';

const QUICK_ACTIONS = [
  'Find fantasy books',
  'Save all books to bookmark',
  'Search authors',
  'My bookmarks',
  'Find highly rated books',
  'Recommend similar books',
];

function formatConversationLabel(conv, index) {
  const firstMessage = (conv.first_message || '').trim();
  if (!firstMessage) return `Conversation ${index + 1}`;
  return firstMessage.length > 42 ? `${firstMessage.slice(0, 42)}...` : firstMessage;
}

function formatConversationTime(conv) {
  const value = conv.last_message_at || conv.created_at;
  if (!value) return '';

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';

  const now = new Date();
  const isToday =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate();

  if (isToday) {
    return `Today, ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
  }

  return date.toLocaleDateString('en-GB');
}

function sortConversationsByRecent(convs) {
  return [...convs].sort((a, b) => {
    const aTime = new Date(a.last_message_at || a.created_at || 0).getTime();
    const bTime = new Date(b.last_message_at || b.created_at || 0).getTime();
    return bTime - aTime;
  });
}

function ThinkingMessage({ progress }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const started = Date.now();
    const interval = setInterval(() => {
      setElapsed(((Date.now() - started) / 1000).toFixed(1));
    }, 100);

    return () => clearInterval(interval);
  }, []);

  const progressText = progress?.[0]?.summary ? ` (${progress[0].summary})` : '';

  return (
    <div className="msg-row ai thinking">
      <div className="msg-label label-ai">Assistant</div>
      <div className="msg-bubble">
        <span className="thinking-label">
          Thinking{progressText}
          <span className="dots"><span></span><span></span><span></span></span>
        </span>
        <span className="thinking-timer">{elapsed}s</span>
      </div>
    </div>
  );
}

function ActivityPanel({ steps = [] }) {
  const [open, setOpen] = useState(false);
  const [openStep, setOpenStep] = useState(null);
  const totalMs = steps.reduce((sum, step) => sum + (step.duration_ms || 0), 0);

  if (!steps.length) return null;

  return (
    <div className={`activity-panel${open ? ' open' : ''}`}>
      <button className="activity-header" type="button" onClick={() => setOpen(!open)}>
        <span className="activity-chevron">{open ? '▼' : '▶'}</span>
        <span className="activity-title">Agent Activity</span>
        <span className="activity-meta">{steps.length} step{steps.length !== 1 ? 's' : ''} · {totalMs}ms</span>
      </button>
      <div className="activity-body">
        {steps.map((step, index) => {
          const statusIcon = step.status === 'completed' ? '✓' : step.status === 'error' ? '✗' : '⟳';
          const toolLabel = (step.tool || 'Unknown Tool').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
          const isOpen = openStep === index;

          return (
            <div className={`activity-step${isOpen ? ' step-open' : ''}`} key={`${toolLabel}-${index}`}>
              <button className="step-header" type="button" onClick={() => setOpenStep(isOpen ? null : index)}>
                <span className={`step-icon ${step.status}`}>{statusIcon}</span>
                <span className="step-name">{toolLabel}</span>
                <span className="step-summary">{step.summary || ''}</span>
                <span className="step-duration">{step.duration_ms ?? '—'}ms</span>
                <span className="step-chevron">{isOpen ? '∨' : '›'}</span>
              </button>
              <div className="step-detail">
                {Object.entries(step.arguments || {}).length ? Object.entries(step.arguments || {}).map(([key, value]) => (
                  <div className="arg-row" key={key}>
                    <span className="arg-key">{key}</span>
                    <span className="arg-val">{typeof value === 'object' ? JSON.stringify(value) : String(value)}</span>
                  </div>
                )) : (
                  <span className="arg-empty">No arguments</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function getWorkKeyFromText(value) {
  const match = String(value || '').match(/\/works\/OL\d+[A-Z]\b|\bOL\d+[A-Z]\b/i);

  if (!match) {
    return null;
  }

  return match[0].startsWith('/works/') ? match[0] : `/works/${match[0]}`;
}

function isBookDetailLine(line) {
  const trimmed = line.trim();

  return (
    !trimmed ||
    /^[-*]\s+/.test(trimmed) ||
    /^\s+/.test(line) ||
    /author|rating|publish|openlibrary|work_key|view on/i.test(trimmed)
  );
}

function buildAssistantSegments(text, bookCards = []) {
  const cardsByWorkKey = new Map(
    bookCards
      .map((book) => [getWorkKeyFromText(book.work_key)?.toLowerCase(), book])
      .filter(([workKey]) => Boolean(workKey))
  );

  if (!cardsByWorkKey.size) {
    return [{ type: 'markdown', text }];
  }

  const lines = String(text || '').split('\n');
  const segments = [];
  let markdownLines = [];
  let index = 0;

  const flushMarkdown = () => {
    const markdown = markdownLines.join('\n').trim();

    if (markdown) {
      segments.push({ type: 'markdown', text: markdown });
    }

    markdownLines = [];
  };

  while (index < lines.length) {
    const line = lines[index];

    if (/^\s*\d+\.\s+/.test(line)) {
      const block = [line];
      index += 1;

      while (index < lines.length && !/^\s*\d+\.\s+/.test(lines[index])) {
        const nextLine = lines[index];
        const followingText = lines.slice(index + 1).find((candidate) => candidate.trim());

        if (
          !nextLine.trim() &&
          followingText &&
          !/^\s*\d+\.\s+/.test(followingText) &&
          !isBookDetailLine(followingText)
        ) {
          break;
        }

        if (nextLine.trim() && !isBookDetailLine(nextLine)) {
          break;
        }

        block.push(nextLine);
        index += 1;
      }

      const blockText = block.join('\n');
      const workKey = getWorkKeyFromText(blockText)?.toLowerCase();
      const book = workKey ? cardsByWorkKey.get(workKey) : null;

      if (book) {
        flushMarkdown();
        segments.push({ type: 'book', book });
      } else {
        markdownLines.push(...block);
      }

      continue;
    }

    markdownLines.push(line);
    index += 1;
  }

  flushMarkdown();
  return segments.length ? segments : [{ type: 'markdown', text }];
}

function ChatMessage({ message, onEdit, onAskSimilar, onTagSearch, onBookmarkSaved }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(message.content || message.text || '');
  const text = message.content ?? message.text ?? '';
  const assistantSegments = useMemo(
    () => buildAssistantSegments(text, message.bookCards || []),
    [text, message.bookCards]
  );

  useEffect(() => {
    setDraft(text);
  }, [text]);

  if (message.type === 'tag-results') {
    return (
      <div className="msg-row ai">
        <div className="msg-label label-ai">Assistant</div>
        <div className="msg-bubble">
          <div className="markdown">
            {message.books.length
              ? `Here are the 5 most highly rated books tagged "${message.tag}".`
              : `Sorry, there aren't any books with the same tag: ${message.tag}.`}
          </div>
          {message.books.map((book) => (
            <BookCard
              book={book}
              key={book.work_key || book.title}
              onAskSimilar={onAskSimilar}
              onTagSearch={onTagSearch}
              onBookmarkSaved={onBookmarkSaved}
            />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className={`msg-row ${message.role}${editing ? ' editing' : ''}`}>
      <div className={`msg-label label-${message.role === 'user' ? 'user' : 'ai'}`}>
        {message.role === 'user' ? 'You' : 'Assistant'}
      </div>
      <div className="msg-bubble">
        {editing ? (
          <>
            <textarea className="message-edit-field" rows="3" value={draft} onChange={(event) => setDraft(event.target.value)} />
            <div className="message-edit-actions">
              <button className="message-edit-cancel" type="button" onClick={() => setEditing(false)}>Cancel</button>
              <button
                className="message-edit-save"
                type="button"
                onClick={() => {
                  setEditing(false);
                  onEdit(message.id, draft);
                }}
              >
                Save
              </button>
            </div>
          </>
        ) : message.role === 'user' ? (
          text
        ) : (
          <>
            {assistantSegments.map((segment, index) => (
              segment.type === 'book' ? (
                <BookCard
                  book={segment.book}
                  key={`${segment.book.work_key || segment.book.title}-${index}`}
                  onAskSimilar={onAskSimilar}
                  onTagSearch={onTagSearch}
                  onBookmarkSaved={onBookmarkSaved}
                />
              ) : (
                <div
                  className="markdown"
                  key={`markdown-${index}`}
                  dangerouslySetInnerHTML={{ __html: renderMarkdown(segment.text) }}
                />
              )
            ))}
            <ActivityPanel steps={message.progress || []} />
          </>
        )}
      </div>
      {message.role === 'user' && message.id ? (
        <button className="message-edit-btn" type="button" onClick={() => setEditing(true)}>Edit</button>
      ) : null}
    </div>
  );
}

function BookmarkList({ refreshKey }) {
  const [bookmarks, setBookmarks] = useState([]);
  const [status, setStatus] = useState('Loading bookmarks...');

  async function fetchBookmarks() {
    setStatus('Loading...');

    try {
      const res = await authFetch(`${API_BASE}/bookmarks`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json();
      setBookmarks(Array.isArray(data) ? data : (data.bookmarks || []));
      setStatus('');
    } catch (err) {
      console.error('Bookmarks error:', err);
      setBookmarks([]);
      setStatus('Could not load bookmarks.');
    }
  }

  useEffect(() => {
    fetchBookmarks();
  }, [refreshKey]);

  return (
    <aside className="sidebar sidebar-right">
      <div className="sidebar-header">
        <span className="sidebar-title">Bookmarks</span>
        <button className="refresh-btn" type="button" title="Refresh" onClick={fetchBookmarks}>↻</button>
      </div>
      <div className="bookmark-list">
        {status ? <p className="sidebar-empty">{status}</p> : null}
        {!status && !bookmarks.length ? <p className="sidebar-empty">No bookmarks yet.</p> : null}
        {bookmarks.map((bookmark) => (
          <div className="bookmark-item" key={bookmark.id || bookmark.work_key}>
            <a
              className="bookmark-link"
              href={normalizeOpenLibraryWorkUrl(bookmark.work_key || '')}
              target="_blank"
              rel="noreferrer"
              title={bookmark.title || 'Open book on OpenLibrary'}
            >
              <div className="bookmark-cover">
                {bookmark.cover_id ? (
                  <img src={getCoverUrl(bookmark.cover_id)} alt={bookmark.title || 'Book cover'} loading="lazy" />
                ) : (
                  <div className="bookmark-cover-fallback">{truncateText(bookmark.title || 'Untitled', 54)}</div>
                )}
              </div>
              <span className="bookmark-title">{bookmark.title || 'Untitled'}</span>
            </a>
            <button
              className="bookmark-remove"
              type="button"
              onClick={async () => {
                try {
                  const res = await authFetch(`${API_BASE}/bookmarks/${bookmark.id || bookmark.work_key}`, { method: 'DELETE' });
                  if (!res.ok) throw new Error(`HTTP ${res.status}`);
                  fetchBookmarks();
                } catch (err) {
                  console.error('Remove bookmark error:', err);
                }
              }}
            >
              Remove
            </button>
          </div>
        ))}
      </div>
    </aside>
  );
}

export default function ChatPage() {
  const [sessionId, setSessionId] = useState(() => crypto.randomUUID());
  const [messages, setMessages] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [loadingConversationId, setLoadingConversationId] = useState(null);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [thinking, setThinking] = useState(null);
  const [showAdminLink, setShowAdminLink] = useState(false);
  const [bookmarkRefreshKey, setBookmarkRefreshKey] = useState(0);
  const chatAreaRef = useRef(null);
  const inputRef = useRef(null);
  const messageCache = useRef(new Map());
  const bookDetailsCache = useRef(new Map());
  const sessionIdRef = useRef(sessionId);
  const sortedConversations = useMemo(() => sortConversationsByRecent(conversations), [conversations]);

  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);

  useEffect(() => {
    getCurrentUser()
      .then((user) => setShowAdminLink(user.role === 'admin'))
      .catch(() => {});
    fetchConversations();
  }, []);

  useEffect(() => {
    if (chatAreaRef.current) {
      chatAreaRef.current.scrollTop = chatAreaRef.current.scrollHeight;
    }
  }, [messages, thinking]);

  const welcomeMode = !messages.length && !thinking;

  async function fetchConversations() {
    const res = await authFetch(`${API_BASE}/conversations/`);

    if (!res.ok) {
      console.error('Failed loading conversations');
      return;
    }

    const data = await res.json();
    setConversations((current) => {
      const optimisticActive = current.find((conv) => conv.session_id === sessionIdRef.current);
      if (
        optimisticActive &&
        optimisticActive.first_message &&
        !data.some((conv) => conv.session_id === sessionIdRef.current)
      ) {
        return [optimisticActive, ...data];
      }
      return data;
    });
  }

  function touchActiveConversation(firstMessage) {
    setConversations((current) => {
      const existing = current.find((conv) => conv.session_id === sessionIdRef.current);

      if (existing) {
        return current.map((conv) => (
          conv.session_id === sessionIdRef.current
            ? {
                ...conv,
                first_message: conv.first_message || firstMessage,
                last_message_at: new Date().toISOString(),
              }
            : conv
        ));
      }

      return [
        {
          session_id: sessionIdRef.current,
          first_message: firstMessage,
          created_at: new Date().toISOString(),
          last_message_at: new Date().toISOString(),
        },
        ...current,
      ];
    });
  }

  async function fetchBookDetails(workKey) {
    if (bookDetailsCache.current.has(workKey)) {
      return bookDetailsCache.current.get(workKey);
    }

    const response = await authFetch(`${API_BASE}/books${workKey}`);

    if (!response.ok) {
      return null;
    }

    const book = await response.json();
    bookDetailsCache.current.set(workKey, book);
    return book;
  }

  async function extractBookCards(answer) {
    const html = renderMarkdown(answer);
    const matches = [
      ...html.matchAll(/href="([^"]*openlibrary\.org\/works\/[^"]+)"/g),
      ...String(answer || '').matchAll(/(\/works\/OL\d+[A-Z]\b|\bOL\d+[A-Z]\b)/gi),
    ];
    const workKeys = [...new Set(matches.map((match) => getWorkKeyFromOpenLibraryUrl(match[1]) || getWorkKeyFromText(match[1])).filter(Boolean))];
    const results = await Promise.allSettled(workKeys.map((workKey) => fetchBookDetails(workKey)));
    return results.map((result) => result.status === 'fulfilled' ? result.value : null).filter(Boolean);
  }

  function cacheMessages(nextSessionId, nextMessages) {
    messageCache.current.set(nextSessionId, nextMessages);
  }

  async function handleSend(messageOverride = null, edit = null) {
    const text = (messageOverride ?? input).trim();
    if (!text || busy) return;

    setInput('');
    setBusy(true);

    let activeSessionId = sessionIdRef.current;
    let userMessage = null;

    if (edit) {
      setMessages((current) => {
        const index = current.findIndex((message) => message.id === edit.messageId);
        const kept = index >= 0 ? current.slice(0, index + 1) : current;
        const updated = kept.map((message) => (
          message.id === edit.messageId ? { ...message, content: text } : message
        ));
        cacheMessages(activeSessionId, updated);
        return updated;
      });
    } else {
      userMessage = {
        localId: crypto.randomUUID(),
        role: 'user',
        content: text,
      };
      setMessages((current) => {
        const next = [...current, userMessage];
        cacheMessages(activeSessionId, next);
        return next;
      });
      touchActiveConversation(text);
      setTimeout(fetchConversations, 350);
    }

    setThinking({ progress: [] });

    try {
      await streamChatResponse(text, activeSessionId, userMessage?.localId, edit?.messageId ?? null);
    } catch (err) {
      console.error('Chat error:', err);
      setMessages((current) => [...current, {
        localId: crypto.randomUUID(),
        role: 'assistant',
        content: 'An error occurred. Please try again.',
        error: true,
      }]);
    } finally {
      setThinking(null);
      setBusy(false);
      inputRef.current?.focus();
    }
  }

  async function streamChatResponse(text, activeSessionId, localUserId, editedMessageId) {
    const body = {
      message: text,
      session_id: activeSessionId,
    };

    if (editedMessageId !== null) {
      body.edited_message_id = editedMessageId;
    }

    const response = await authFetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

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
          await appendAssistantAnswer(activeSessionId, answer, progress);
        }
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
            setThinking({ progress });
          }

          if (data.type === 'user_message' && localUserId) {
            setMessages((current) => {
              const next = current.map((message) => (
                message.localId === localUserId ? { ...message, id: data.id } : message
              ));
              cacheMessages(activeSessionId, next);
              return next;
            });
          }

          if (data.type === 'delta') {
            answer += data.delta;
            setThinking(null);
            upsertStreamingAssistant(activeSessionId, answer, progress);
          }

          if (data.type === 'complete') {
            if (data.progress) progress = data.progress;
            await appendAssistantAnswer(activeSessionId, answer, progress);
            finalRendered = true;
            setTimeout(fetchConversations, 300);
          }
        } catch (error) {
          console.log('Invalid SSE:', event);
        }
      }
    }
  }

  function upsertStreamingAssistant(activeSessionId, answer, progress) {
    setMessages((current) => {
      const withoutStreaming = current.filter((message) => message.localId !== 'streaming-assistant');
      const next = [...withoutStreaming, {
        localId: 'streaming-assistant',
        role: 'assistant',
        content: answer,
        progress,
      }];
      cacheMessages(activeSessionId, next);
      return next;
    });
  }

  async function appendAssistantAnswer(activeSessionId, answer, progress) {
    const bookCards = await extractBookCards(answer);

    setMessages((current) => {
      const withoutStreaming = current.filter((message) => message.localId !== 'streaming-assistant');
      const next = [...withoutStreaming, {
        localId: crypto.randomUUID(),
        role: 'assistant',
        content: answer,
        progress,
        bookCards,
      }];
      cacheMessages(activeSessionId, next);
      return next;
    });
  }

  async function switchConversation(nextSessionId) {
    setSessionId(nextSessionId);

    if (messageCache.current.has(nextSessionId)) {
      setMessages(messageCache.current.get(nextSessionId));
      setLoadingConversationId(null);
    } else {
      setLoadingConversationId(nextSessionId);
    }

    try {
      const res = await authFetch(`${API_BASE}/conversations/${nextSessionId}`);
      if (!res.ok) throw new Error('Conversation load failed');

      const data = await res.json();
      const normalized = data
        .filter((message) => message.role !== 'system')
        .map((message) => ({
          localId: crypto.randomUUID(),
          id: message.id,
          role: message.role,
          content: message.text ?? message.content ?? '',
        }));

      messageCache.current.set(nextSessionId, normalized);

      if (sessionIdRef.current === nextSessionId) {
        setMessages(normalized);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingConversationId(null);
    }
  }

  function newConversation() {
    const nextSessionId = crypto.randomUUID();
    setSessionId(nextSessionId);
    setMessages([]);
    setLoadingConversationId(null);
    messageCache.current.set(nextSessionId, []);
  }

  async function deleteConversation(nextSessionId) {
    setConversations((current) => current.filter((conv) => conv.session_id !== nextSessionId));

    try {
      const res = await authFetch(`${API_BASE}/conversations/${nextSessionId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      if (nextSessionId === sessionIdRef.current) {
        newConversation();
      }
    } catch (err) {
      console.error('Delete conversation error:', err);
      fetchConversations();
    }
  }

  async function clearConversations() {
    setConversations([]);
    newConversation();

    try {
      const res = await authFetch(`${API_BASE}/conversations/`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
    } catch (err) {
      console.error('Clear conversations error:', err);
      fetchConversations();
    }
  }

  async function showTopRatedBooksByTag(tag) {
    setMessages((current) => [...current, {
      localId: crypto.randomUUID(),
      role: 'user',
      content: `Show highly rated books tagged "${tag}"`,
    }]);
    setThinking({ progress: [] });

    try {
      const response = await authFetch(`${API_BASE}/books/top-rated-by-tag?tag=${encodeURIComponent(tag)}&limit=5`);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const books = await response.json();
      setMessages((current) => [...current, {
        localId: crypto.randomUUID(),
        role: 'assistant',
        type: 'tag-results',
        tag,
        books,
      }]);
    } catch (error) {
      console.log('Could not load books by tag:', error);
      setMessages((current) => [...current, {
        localId: crypto.randomUUID(),
        role: 'assistant',
        content: 'Could not load books with this tag.',
      }]);
    } finally {
      setThinking(null);
    }
  }

  return (
    <div className="app-shell">
      <TopBar title="QuynhNhiVu" subtitle="AI Book Retrieval" showAdminLink={showAdminLink} />
      <div className="body-columns">
        <aside className="sidebar sidebar-left">
          <div className="sidebar-header">
            <span className="sidebar-title">Conversations</span>
            <div className="sidebar-actions">
              <button className="clear-chat-btn" type="button" title="Delete all conversations" onClick={clearConversations}>Clear</button>
              <button className="new-chat-btn" type="button" title="New conversation" onClick={newConversation}>＋ New</button>
            </div>
          </div>
          <div className="conv-list">
            {!sortedConversations.length ? <p className="sidebar-empty">No conversations yet.</p> : null}
            {sortedConversations.map((conv, index) => (
              <div
                className={`conv-item${conv.session_id === sessionId ? ' active' : ''}${conv.session_id === loadingConversationId ? ' loading' : ''}`}
                key={conv.session_id}
                onClick={() => switchConversation(conv.session_id)}
              >
                <span className="conv-item-text">
                  <span className="conv-item-label">{formatConversationLabel(conv, index)}</span>
                  <span className="conv-item-time">{formatConversationTime(conv)}</span>
                </span>
                <button
                  className="conv-delete"
                  type="button"
                  title="Delete conversation"
                  onClick={(event) => {
                    event.stopPropagation();
                    deleteConversation(conv.session_id);
                  }}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </aside>

        <main className={`chat-column${welcomeMode ? ' welcome-mode' : ''}`}>
          <div className="chat-area" ref={chatAreaRef}>
            {welcomeMode ? (
              <div className="welcome">
                <p className="welcome-hint">How can I help you explore OpenLibrary?</p>
                <p className="welcome-subtitle">Search by author, genre, rating, bookmarks, or similar books.</p>
              </div>
            ) : null}
            {messages.map((message) => (
              <ChatMessage
                message={message}
                key={message.localId || message.id}
                onAskSimilar={(prompt) => handleSend(prompt)}
                onTagSearch={showTopRatedBooksByTag}
                onBookmarkSaved={() => setBookmarkRefreshKey((value) => value + 1)}
                onEdit={(messageId, value) => handleSend(value, { messageId })}
              />
            ))}
            {thinking ? <ThinkingMessage progress={thinking.progress} /> : null}
          </div>

          <div className="quick-actions" aria-label="Quick actions">
            <div className="quick-actions-label">Quick Actions</div>
            <div className="quick-actions-list">
              {QUICK_ACTIONS.map((prompt) => (
                <button className="quick-action-btn" type="button" key={prompt} onClick={() => handleSend(prompt)}>
                  {prompt}
                </button>
              ))}
            </div>
          </div>

          <div className="input-bar">
            <textarea
              ref={inputRef}
              className="input-field"
              placeholder="e.g. Find history books rated above 4..."
              rows="1"
              autoComplete="off"
              spellCheck="false"
              value={input}
              disabled={busy}
              onChange={(event) => {
                setInput(event.target.value);
                event.target.style.height = 'auto';
                event.target.style.height = `${Math.min(event.target.scrollHeight, 140)}px`;
              }}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault();
                  handleSend();
                }
              }}
            />
            <button className="send-btn" type="button" aria-label="Send" disabled={busy} onClick={() => handleSend()}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
              </svg>
            </button>
          </div>
        </main>

        <BookmarkList refreshKey={bookmarkRefreshKey} />
      </div>
    </div>
  );
}
