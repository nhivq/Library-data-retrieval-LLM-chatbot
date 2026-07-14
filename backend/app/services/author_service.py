from psycopg2.extras import RealDictCursor
from backend.app.core.cache import get_json, make_cache_key, set_json


AUTHOR_DETAIL_CACHE_TTL_SECONDS = 60 * 60 * 24
AUTHOR_LIST_CACHE_TTL_SECONDS = 60 * 30

def get_author(
        author_key: str,
        conn = None
):
    """Fetch one author and aggregate the titles connected to that author."""

    cache_key = make_cache_key(
        "author:detail",
        {
            "author_key": author_key
        }
    )

    cached_author = get_json(cache_key)

    if cached_author is not None:
        return cached_author

    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:

        query = """
                SELECT a.author_key, 
                       a.author_name, 

                       ARRAY_AGG(b.title) AS books

                FROM authors a

                        LEFT JOIN book_authors ba
                              ON a.author_key = ba.author_key

                        LEFT JOIN books b
                              ON ba.work_key = b.work_key

                WHERE a.author_key LIKE %s

                GROUP BY a.author_key, 
                         a.author_name 
                """

        cursor.execute(query, (author_key,))

        author = cursor.fetchone()

        set_json(
            cache_key,
            author,
            ttl_seconds=AUTHOR_DETAIL_CACHE_TTL_SECONDS
        )

        return author

    finally:
        cursor.close()


def search_authors(
        author_name: str | None = None,
        author_starts_with: str | None = None,
        author_ends_with: str | None = None,
        author_key: str | None = None,
        conn=None
):
    """Search authors by flexible name/key filters."""

    cache_key = make_cache_key(
        "author:search",
        {
            "author_name": author_name,
            "author_starts_with": author_starts_with,
            "author_ends_with": author_ends_with,
            "author_key": author_key
        }
    )

    cached_authors = get_json(cache_key)

    if cached_authors is not None:
        return cached_authors

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        query = """
                SELECT a.author_key,
                       a.author_name,

                       ARRAY_AGG(b.title) AS books

                FROM authors a

                         LEFT JOIN book_authors ba
                               ON a.author_key = ba.author_key

                         LEFT JOIN books b
                               ON ba.work_key = b.work_key

                WHERE 1 = 1
              """

        # Build WHERE clauses only for filters the caller provided.
        params = []

        if author_starts_with:
            query += """
                    AND a.author_name ILIKE %s
                    """
            params.append(f"{author_starts_with}%")

        if author_ends_with:
            query += """
                    AND a.author_name ILIKE %s
                    """
            params.append(f"%{author_ends_with}")

        if author_name:
            query += """
                    AND a.author_name ILIKE %s
                    """
            params.append(f"%{author_name}%")

        if author_key:
            query += """
                    AND a.author_key ILIKE %s
                    """
            params.append(f"%{author_key}%")

        query += """
                GROUP BY a.author_key,
                         a.author_name
              """

        cursor.execute(query, params)

        authors = cursor.fetchall()

        set_json(
            cache_key,
            authors,
            ttl_seconds=AUTHOR_LIST_CACHE_TTL_SECONDS
        )

        return authors

    finally:
        cursor.close()


def get_authors(
        page: int = 1,
        limit: int = 10,
        conn=None
):
    """Return a paginated author list with each author's books."""

    if page < 1:
        page = 1

    if limit < 1:
        limit = 10

    if limit > 100:
        limit = 100

    cache_key = make_cache_key(
        "author:list",
        {
            "page": page,
            "limit": limit
        }
    )

    cached_authors = get_json(cache_key)

    if cached_authors is not None:
        return cached_authors

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:

        offset = (page - 1) * limit

        query = """
                SELECT a.author_key,
                       a.author_name,

                       COALESCE(
                           ARRAY_AGG(b.title)
                           FILTER (WHERE b.title IS NOT NULL),
                           ARRAY[]::text[]
                       ) AS books

                FROM authors a

                         LEFT JOIN book_authors ba
                               ON a.author_key = ba.author_key

                         LEFT JOIN books b
                               ON ba.work_key = b.work_key

                GROUP BY a.author_key,
                         a.author_name

                ORDER BY a.author_name ASC

                LIMIT %s
                OFFSET %s
              """

        cursor.execute(query, (limit, offset))

        authors = cursor.fetchall()

        set_json(
            cache_key,
            authors,
            ttl_seconds=AUTHOR_LIST_CACHE_TTL_SECONDS
        )

        return authors

    finally:
        cursor.close()
