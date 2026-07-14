export function escapeHtml(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export function truncateText(value, maxLength) {
  const text = String(value || '').trim();
  return text.length <= maxLength
    ? text
    : `${text.slice(0, maxLength - 3).trim()}...`;
}

export function normalizeOpenLibraryWorkUrl(value) {
  const workKeyMatch = String(value).match(
    /\/works\/OL\d+[A-Z]\b|\bOL\d+[A-Z]\b/i
  );

  if (!workKeyMatch) {
    return value || 'https://openlibrary.org';
  }

  const workKey = workKeyMatch[0].startsWith('/works/')
    ? workKeyMatch[0]
    : `/works/${workKeyMatch[0]}`;

  return `https://openlibrary.org${workKey}`;
}

export function getWorkKeyFromOpenLibraryUrl(value) {
  const match = String(value).match(/\/works\/OL\d+[A-Z]\b/i);
  return match ? match[0] : null;
}

export function getCoverUrl(coverId) {
  return `https://covers.openlibrary.org/b/id/${coverId}-M.jpg`;
}

export function formatDate(value) {
  if (!value) {
    return null;
  }

  const date = new Date(`${value}T00:00:00`);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

export function formatNumber(value) {
  if (value === null || value === undefined) {
    return 'N/A';
  }

  return Number(value).toLocaleString();
}

export function renderMarkdown(text) {
  let html = escapeHtml(text);

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
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
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
      flushOrdered();
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

  return out.join('\n');
}
