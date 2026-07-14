import { API_BASE, authFetch } from '../api/client.js';
import { formatDate, getCoverUrl, normalizeOpenLibraryWorkUrl, truncateText } from '../utils.js';

function formatAuthors(authors) {
  return authors?.length ? authors.slice(0, 3).join(', ') : 'Unavailable';
}

function formatRating(rating) {
  return rating === null || rating === undefined ? 'Unavailable' : Number(rating).toFixed(1);
}

export default function BookCard({ book, onAskSimilar, onTagSearch, onBookmarkSaved }) {
  async function saveBookmark(event) {
    const button = event.currentTarget;
    const originalText = button.textContent;
    button.disabled = true;
    button.textContent = 'Saving...';

    try {
      const response = await authFetch(`${API_BASE}/bookmarks/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ work_key: book.work_key }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      button.textContent = 'Bookmarked';
      onBookmarkSaved?.();
    } catch (error) {
      console.log('Could not save bookmark:', error);
      button.disabled = false;
      button.textContent = originalText;
    }
  }

  return (
    <div className="book-result-card">
      <div className="book-cover-card">
        <div className="book-cover-frame">
          {book.cover_id ? (
            <img className="book-cover-img" src={getCoverUrl(book.cover_id)} alt={book.title || 'Book cover'} loading="lazy" />
          ) : (
            <div className="book-cover-fallback">
              <div className="book-cover-title">{truncateText(book.title || 'Untitled book', 72)}</div>
              {book.authors?.length ? (
                <div className="book-cover-authors">{truncateText(book.authors.join(', '), 44)}</div>
              ) : null}
            </div>
          )}
        </div>
      </div>
      <div className="book-result-details">
        <a className="book-result-title" href={normalizeOpenLibraryWorkUrl(book.work_key)} target="_blank" rel="noreferrer">
          {book.title || 'Untitled book'}
        </a>
        <div className="book-meta-row"><span className="book-meta-label">Author</span><span className="book-meta-value">{formatAuthors(book.authors)}</span></div>
        <div className="book-meta-row"><span className="book-meta-label">Rating</span><span className="book-meta-value">{formatRating(book.rating)}</span></div>
        <div className="book-meta-row"><span className="book-meta-label">Published</span><span className="book-meta-value">{formatDate(book.publish_date) || 'Unavailable'}</span></div>
        <div className="book-tag-row">
          {(book.tags || []).slice(0, 4).map((tag) => (
            <button className="book-tag-pill" type="button" key={tag} onClick={() => onTagSearch?.(tag)}>
              {tag}
            </button>
          ))}
        </div>
        <div className="book-actions">
          <button className="book-action-btn" type="button" onClick={saveBookmark}>Bookmark</button>
          <button
            className="book-action-btn"
            type="button"
            onClick={() => onAskSimilar?.(`Find books similar to ${book.title} with work_key: ${book.work_key}`)}
          >
            Find Similar Books
          </button>
        </div>
      </div>
    </div>
  );
}
