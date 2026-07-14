import { useEffect, useState } from 'react';
import { API_BASE, authFetch, getCurrentUser, logout, routeTo } from '../api/client.js';
import TopBar from '../components/TopBar.jsx';
import { formatNumber } from '../utils.js';

const TOTAL_LABELS = {
  books: 'Books',
  authors: 'Authors',
  editions: 'Editions',
  book_author_links: 'Book-author links',
  users: 'Users',
  bookmarks: 'Bookmarks',
  conversations: 'Conversations',
};

const QUALITY_LABELS = {
  books_without_authors: 'Books without authors',
  authors_without_books: 'Authors without books',
  duplicate_author_names: 'Duplicate author names',
  books_without_publish_date: 'Books without publish date',
  books_without_rating: 'Books without rating',
  books_without_description: 'Books without description',
  authors_without_bio: 'Authors without bio',
};

function formatAdminDate(value) {
  return value ? new Date(value).toLocaleDateString() : 'N/A';
}

export default function AdminPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  async function loadDashboard() {
    setLoading(true);
    setError('');

    try {
      const res = await authFetch(`${API_BASE}/admin/analytics`);

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      setData(await res.json());
    } catch (err) {
      console.error(err);
      setError('Could not load dashboard.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let mounted = true;

    getCurrentUser()
      .then((user) => {
        if (!mounted) return;

        if (user.role !== 'admin') {
          routeTo('/chat');
          return;
        }

        loadDashboard();
      })
      .catch(() => logout());

    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="admin-shell">
      <TopBar title="Admin Dashboard" subtitle="Library Dataset Analytics" chatLink />
      <main className="dashboard">
        <section className="summary-grid" aria-label="Dataset totals">
          {loading && !data ? (
            <p className="muted">Loading dashboard...</p>
          ) : error ? (
            <p className="error">{error}</p>
          ) : (
            Object.entries(TOTAL_LABELS).map(([key, label]) => (
              <article className="metric-card" key={key}>
                <span className="metric-label">{label}</span>
                <strong className="metric-value">{formatNumber(data?.totals?.[key] ?? 0)}</strong>
              </article>
            ))
          )}
        </section>

        <section className="dashboard-grid">
          <div className="panel panel-wide">
            <div className="panel-header">
              <h2>Data Quality</h2>
              <button className="refresh-btn" type="button" onClick={loadDashboard} disabled={loading}>
                Refresh
              </button>
            </div>
            <div className="quality-grid">
              {Object.entries(QUALITY_LABELS).map(([key, label]) => {
                const value = data?.data_quality?.[key];
                const unavailable = value === null || value === undefined;

                return (
                  <div className={`quality-item${unavailable ? ' is-muted' : ''}`} key={key}>
                    <span>{label}</span>
                    <strong>{formatNumber(value)}</strong>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="panel">
            <div className="panel-header"><h2>Top Authors</h2></div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr><th>Author</th><th>Books</th></tr>
                </thead>
                <tbody>
                  {data?.top_authors?.length ? data.top_authors.map((author) => (
                    <tr key={author.author_name}>
                      <td>{author.author_name}</td>
                      <td>{formatNumber(author.book_count)}</td>
                    </tr>
                  )) : (
                    <tr><td colSpan="2" className="empty">No author data.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="panel">
            <div className="panel-header"><h2>Top Tags</h2></div>
            <div className="tag-list">
              {data?.top_tags?.length ? data.top_tags.map((tag) => (
                <div className="tag-row" key={tag.tag}>
                  <span>{tag.tag}</span>
                  <strong>{formatNumber(tag.book_count)}</strong>
                </div>
              )) : (
                <p className="empty">No tag data.</p>
              )}
            </div>
          </div>

          <div className="panel panel-wide">
            <div className="panel-header"><h2>Recent Books</h2></div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr><th>Title</th><th>Work Key</th><th>Created</th></tr>
                </thead>
                <tbody>
                  {data?.recent_books?.length ? data.recent_books.map((book) => (
                    <tr key={book.work_key}>
                      <td>{book.title}</td>
                      <td><code>{book.work_key}</code></td>
                      <td>{formatAdminDate(book.created_at)}</td>
                    </tr>
                  )) : (
                    <tr><td colSpan="3" className="empty">No recent books.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
