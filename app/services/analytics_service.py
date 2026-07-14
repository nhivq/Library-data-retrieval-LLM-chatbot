from psycopg2.extras import RealDictCursor

from app.core.cache import get_json, set_json


ADMIN_ANALYTICS_CACHE_KEY = "admin:analytics:v1"
ADMIN_ANALYTICS_CACHE_TTL_SECONDS = 60 * 5


def _table_exists(cursor, table_name: str) -> bool:
    """Check whether an optional table exists before querying it."""

    cursor.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = %s
        )
        """,
        (table_name,)
    )

    return cursor.fetchone()["exists"]


def _column_exists(cursor, table_name: str, column_name: str) -> bool:
    """Check whether an optional column exists before querying it."""

    cursor.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = %s
              AND column_name = %s
        )
        """,
        (table_name, column_name)
    )

    return cursor.fetchone()["exists"]


def _count_table(cursor, table_name: str) -> int:
    """Return table size, treating missing optional tables as empty."""

    if not _table_exists(cursor, table_name):
        return 0

    cursor.execute(f"SELECT COUNT(*) AS total FROM {table_name}")

    return cursor.fetchone()["total"]


def _count_missing_column(cursor, table_name: str, column_name: str) -> int | None:
    """Count NULL values for a column, or None if the column is unavailable."""

    if not _table_exists(cursor, table_name):
        return None

    if not _column_exists(cursor, table_name, column_name):
        return None

    cursor.execute(
        f"""
        SELECT COUNT(*) AS total
        FROM {table_name}
        WHERE {column_name} IS NULL
        """
    )

    return cursor.fetchone()["total"]


def _count_blank_column(cursor, table_name: str, column_name: str) -> int | None:
    """Count NULL or blank text values for data quality checks."""

    if not _table_exists(cursor, table_name):
        return None

    if not _column_exists(cursor, table_name, column_name):
        return None

    cursor.execute(
        f"""
        SELECT COUNT(*) AS total
        FROM {table_name}
        WHERE {column_name} IS NULL
           OR BTRIM({column_name}) = ''
        """
    )

    return cursor.fetchone()["total"]


def _get_data_quality(cursor) -> dict:
    """Collect counts that help spot incomplete imported library data."""

    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM books b
        LEFT JOIN book_authors ba
               ON b.work_key = ba.work_key
        WHERE ba.work_key IS NULL
        """
    )
    books_without_authors = cursor.fetchone()["total"]

    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM authors a
        LEFT JOIN book_authors ba
               ON a.author_key = ba.author_key
        WHERE ba.author_key IS NULL
        """
    )
    authors_without_books = cursor.fetchone()["total"]

    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM (
            SELECT LOWER(BTRIM(author_name)) AS normalized_name
            FROM authors
            GROUP BY LOWER(BTRIM(author_name))
            HAVING COUNT(*) > 1
        ) duplicate_names
        """
    )
    duplicate_author_names = cursor.fetchone()["total"]

    return {
        "books_without_authors": books_without_authors,
        "authors_without_books": authors_without_books,
        "duplicate_author_names": duplicate_author_names,
        "books_without_publish_date": _count_missing_column(
            cursor,
            "books",
            "publish_date"
        ),
        "books_without_rating": _count_missing_column(
            cursor,
            "books",
            "rating"
        ),
        "books_without_description": _count_blank_column(
            cursor,
            "books",
            "description"
        ),
        "authors_without_bio": _count_blank_column(
            cursor,
            "authors",
            "bio"
        )
    }


def _get_top_authors(cursor) -> list[dict]:
    """Return authors with the largest number of linked books."""

    cursor.execute(
        """
        SELECT a.author_key,
               a.author_name,
               COUNT(ba.work_key) AS book_count
        FROM authors a
        JOIN book_authors ba
             ON a.author_key = ba.author_key
        GROUP BY a.author_key,
                 a.author_name
        ORDER BY book_count DESC,
                 a.author_name ASC
        LIMIT 10
        """
    )

    return [dict(row) for row in cursor.fetchall()]


def _get_top_tags(cursor) -> list[dict]:
    """Return the most common book tags from the tags array column."""

    if not _column_exists(cursor, "books", "tags"):
        return []

    cursor.execute(
        """
        SELECT tag,
               COUNT(*) AS book_count
        FROM books,
             UNNEST(tags) AS tag
        WHERE tag IS NOT NULL
          AND BTRIM(tag) != ''
        GROUP BY tag
        ORDER BY book_count DESC,
                 tag ASC
        LIMIT 10
        """
    )

    return [dict(row) for row in cursor.fetchall()]


def _get_recent_books(cursor) -> list[dict]:
    """Return recently inserted books when created_at exists."""

    if _column_exists(cursor, "books", "created_at"):
        cursor.execute(
            """
            SELECT work_key,
                   title,
                   created_at
            FROM books
            ORDER BY created_at DESC NULLS LAST,
                     work_key DESC
            LIMIT 10
            """
        )

    else:
        cursor.execute(
            """
            SELECT work_key,
                   title
            FROM books
            ORDER BY work_key DESC
            LIMIT 10
            """
        )

    return [dict(row) for row in cursor.fetchall()]


def get_dashboard_analytics(conn=None) -> dict:
    """Build the admin dashboard analytics payload."""

    cached_dashboard = get_json(
        ADMIN_ANALYTICS_CACHE_KEY
    )

    if cached_dashboard is not None:
        return cached_dashboard

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        totals = {
            "books": _count_table(cursor, "books"),
            "authors": _count_table(cursor, "authors"),
            "book_author_links": _count_table(cursor, "book_authors"),
            "editions": _count_table(cursor, "editions"),
            "users": _count_table(cursor, "users"),
            "bookmarks": _count_table(cursor, "bookmarks"),
            "conversations": _count_table(cursor, "conversations")
        }

        dashboard = {
            "totals": totals,
            "data_quality": _get_data_quality(cursor),
            "top_authors": _get_top_authors(cursor),
            "top_tags": _get_top_tags(cursor),
            "recent_books": _get_recent_books(cursor)
        }

        set_json(
            ADMIN_ANALYTICS_CACHE_KEY,
            dashboard,
            ttl_seconds=ADMIN_ANALYTICS_CACHE_TTL_SECONDS
        )

        return dashboard

    finally:

        cursor.close()
