const summaryGrid = document.getElementById("summaryGrid");
const qualityGrid = document.getElementById("qualityGrid");
const topAuthorsBody = document.getElementById("topAuthorsBody");
const topTagsList = document.getElementById("topTagsList");
const recentBooksBody = document.getElementById("recentBooksBody");
const refreshBtn = document.getElementById("refreshBtn");

document.getElementById("logoutBtn").addEventListener("click", logout);
refreshBtn.addEventListener("click", loadDashboard);

const TOTAL_LABELS = {
  books: "Books",
  authors: "Authors",
  editions: "Editions",
  book_author_links: "Book-author links",
  users: "Users",
  bookmarks: "Bookmarks",
  conversations: "Conversations",
};

const QUALITY_LABELS = {
  books_without_authors: "Books without authors",
  authors_without_books: "Authors without books",
  duplicate_author_names: "Duplicate author names",
  books_without_publish_date: "Books without publish date",
  books_without_rating: "Books without rating",
  books_without_description: "Books without description",
  authors_without_bio: "Authors without bio",
};

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatNumber(value) {
  if (value === null || value === undefined) {
    return "N/A";
  }

  return Number(value).toLocaleString();
}

function formatDate(value) {
  if (!value) {
    return "N/A";
  }

  return new Date(value).toLocaleDateString();
}

function setLoading() {
  summaryGrid.innerHTML = '<p class="muted">Loading dashboard...</p>';
  qualityGrid.innerHTML = "";
  topAuthorsBody.innerHTML = "";
  topTagsList.innerHTML = "";
  recentBooksBody.innerHTML = "";
}

function renderTotals(totals) {
  summaryGrid.innerHTML = Object.entries(TOTAL_LABELS)
    .map(([key, label]) => {
      const value = totals?.[key] ?? 0;

      return `
        <article class="metric-card">
          <span class="metric-label">${escapeHtml(label)}</span>
          <strong class="metric-value">${formatNumber(value)}</strong>
        </article>
      `;
    })
    .join("");
}

function renderQuality(dataQuality) {
  qualityGrid.innerHTML = Object.entries(QUALITY_LABELS)
    .map(([key, label]) => {
      const value = dataQuality?.[key];
      const unavailable = value === null || value === undefined;

      return `
        <div class="quality-item${unavailable ? " is-muted" : ""}">
          <span>${escapeHtml(label)}</span>
          <strong>${formatNumber(value)}</strong>
        </div>
      `;
    })
    .join("");
}

function renderTopAuthors(topAuthors) {
  if (!topAuthors?.length) {
    topAuthorsBody.innerHTML = '<tr><td colspan="2" class="empty">No author data.</td></tr>';
    return;
  }

  topAuthorsBody.innerHTML = topAuthors
    .map((author) => `
      <tr>
        <td>${escapeHtml(author.author_name)}</td>
        <td>${formatNumber(author.book_count)}</td>
      </tr>
    `)
    .join("");
}

function renderTopTags(topTags) {
  if (!topTags?.length) {
    topTagsList.innerHTML = '<p class="empty">No tag data.</p>';
    return;
  }

  topTagsList.innerHTML = topTags
    .map((tag) => `
      <div class="tag-row">
        <span>${escapeHtml(tag.tag)}</span>
        <strong>${formatNumber(tag.book_count)}</strong>
      </div>
    `)
    .join("");
}

function renderRecentBooks(recentBooks) {
  if (!recentBooks?.length) {
    recentBooksBody.innerHTML = '<tr><td colspan="3" class="empty">No recent books.</td></tr>';
    return;
  }

  recentBooksBody.innerHTML = recentBooks
    .map((book) => `
      <tr>
        <td>${escapeHtml(book.title)}</td>
        <td><code>${escapeHtml(book.work_key)}</code></td>
        <td>${formatDate(book.created_at)}</td>
      </tr>
    `)
    .join("");
}

async function loadDashboard() {
  setLoading();
  refreshBtn.disabled = true;

  try {
    const res = await authFetch(`${API_BASE}/admin/analytics`);

    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }

    const data = await res.json();

    renderTotals(data.totals);
    renderQuality(data.data_quality);
    renderTopAuthors(data.top_authors);
    renderTopTags(data.top_tags);
    renderRecentBooks(data.recent_books);
  } catch (err) {
    summaryGrid.innerHTML = '<p class="error">Could not load dashboard.</p>';
    console.error(err);
  } finally {
    refreshBtn.disabled = false;
  }
}

async function initAdminDashboard() {
  const user = await requireAdmin();

  if (!user) {
    return;
  }

  loadDashboard();
}

initAdminDashboard();
