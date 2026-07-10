import re
from psycopg2.extras import Json, RealDictCursor
from app.core.cache import get_json, make_cache_key, set_json
from app.semantic.embeddings import embed_text, format_vector


BOOK_DETAIL_CACHE_TTL_SECONDS = 60 * 60 * 24
BOOK_LIST_CACHE_TTL_SECONDS = 60 * 30
BOOK_SEARCH_CACHE_TTL_SECONDS = 60 * 15
BOOK_RECOMMENDATION_CACHE_TTL_SECONDS = 60 * 30
BOOK_TAG_CACHE_TTL_SECONDS = 60 * 30


# Words that are too general to help keyword recommendations.
# The LLM is expected to expand user intent into useful concepts before
# calling recommend_books; this list only removes filler words.
RECOMMENDATION_STOP_WORDS = {
    "a",
    "an",
    "and",
    "also",
    "book",
    "books",
    "for",
    "give",
    "having",
    "i",
    "is",
    "me",
    "of",
    "that",
    "the",
    "to",
    "want",
    "with",
}


def extract_recommendation_terms(prompt: str):
    """Extract stable, unique recommendation keywords from free text."""

    words = re.findall(
        r"[a-zA-Z]+",
        prompt.lower()
    )

    terms = []

    for word in words:

        if word in RECOMMENDATION_STOP_WORDS:
            continue

        terms.append(word)

    # Keep term order stable while removing duplicates.
    # Semantic expansion should happen in the LLM/tool call, not in a fixed backend map.
    return list(dict.fromkeys(terms))


def build_recommendation_groups(
        prompt: str,
        concept_groups: list[str] | None = None
):
    """Prepare concept groups for the SQL recommendation CTE.

    Each group represents one user intent, such as setting, theme, or tone.
    Books that match more groups are ranked higher than books that match many
    words from only one group.
    """

    groups = concept_groups or [prompt]
    prepared_groups = []

    for index, group in enumerate(groups, start=1):

        terms = extract_recommendation_terms(group)

        if not terms:
            continue

        prepared_groups.append(
            {
                "group_id": index,
                "terms": terms
            }
        )

    return prepared_groups


def build_book_embedding_text(book: dict) -> str:
    """Build the text used to create a book embedding.

    Keeping this in one place helps ingestion and search use the same meaning
    of "book content" when vector embeddings are generated or refreshed.
    """

    parts = [
        book.get("title"),
        book.get("description"),
        ", ".join(book.get("authors") or []),
        ", ".join(book.get("tags") or []),
        ", ".join(book.get("languages") or []),
        ", ".join(book.get("publishers") or []),
    ]

    return "\n".join(
        part
        for part in parts
        if part
    )

def get_books(
        limit: int = 10,
        conn=None
):
    """Return the first books with their author names aggregated."""

    if limit < 1:
        limit = 10

    if limit > 100:
        limit = 100

    cache_key = make_cache_key(
        "book:list",
        {
            "limit": limit
        }
    )

    cached_books = get_json(cache_key)

    if cached_books is not None:
        return cached_books

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:

        query = """
                SELECT b.work_key,
                       b.title,
                       b.tags,
                       b.publish_date,
                       b.rating,
                       b.cover_id,
                       COALESCE(
                           ARRAY_AGG(a.author_name)
                           FILTER (WHERE a.author_name IS NOT NULL),
                           ARRAY[]::text[]
                       ) AS authors

                FROM books b

                         LEFT JOIN book_authors ba
                                   ON b.work_key = ba.work_key

                         LEFT JOIN authors a
                                   ON ba.author_key = a.author_key

                GROUP BY b.work_key,
                         b.title,
                         b.tags,
                         b.publish_date,
                         b.rating,
                         b.cover_id

                LIMIT %s 
                """

        # Parameterized queries keep user-controlled values out of the SQL text.
        cursor.execute(query, (limit,))

        books = cursor.fetchall()

        set_json(
            cache_key,
            books,
            ttl_seconds=BOOK_LIST_CACHE_TTL_SECONDS
        )

        return books

    finally:

        cursor.close()


def search_books(
        q: str | None = None,
        author: str | None = None,
        min_rating: float | None = None,
        tag: str | None = None,
        published_before_year: int | None = None,
        published_after_year: int | None = None,
        published_year: int | None = None,
        page:int=1,
        limit:int=10,
        conn = None
):
    """Search books using strict filters supplied by the API or MCP tool."""

    if page < 1:
        page = 1

    if limit < 1:
        limit = 10

    if limit > 100:
        limit = 100

    cache_key = make_cache_key(
        "book:search",
        {
            "q": q,
            "author": author,
            "min_rating": min_rating,
            "tag": tag,
            "published_before_year": published_before_year,
            "published_after_year": published_after_year,
            "published_year": published_year,
            "page": page,
            "limit": limit
        }
    )

    cached_books = get_json(cache_key)

    if cached_books is not None:
        return cached_books

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:

        # Aggregate authors while preserving books that do not have author rows.
        # COALESCE keeps the API response shape stable by returning [].
        query = """
                SELECT b.work_key,
                       b.title,
                       b.tags,
                       b.publish_date,
                       b.rating,
                       b.cover_id,
                       COALESCE(  
                           ARRAY_AGG(a.author_name) 
                           FILTER (WHERE a.author_name IS NOT NULL),
                           ARRAY[]::text[]
                       ) AS authors

                FROM books b 

                         LEFT JOIN book_authors ba 
                                   ON b.work_key = ba.work_key 

                         LEFT JOIN authors a 
                                   ON ba.author_key = a.author_key 

                WHERE 1 = 1 
              """

        params = []

        if q:
            # PostgreSQL regex word boundaries avoid substring surprises such
            # as "art" matching "cartoon".
            query += """
                AND b.title ~* %s 
                """

            params.append(
                fr"\m{q}\M"
            )

        if author:
            # EXISTS filters by author without changing the outer aggregation
            # of all authors for the matching book.
            query += """
            AND EXISTS (
                SELECT 1
                FROM book_authors filter_ba
                         JOIN authors filter_a
                              ON filter_ba.author_key = filter_a.author_key
                WHERE filter_ba.work_key = b.work_key
                  AND filter_a.author_name ILIKE %s
            )
            """

            params.append(f"%{author}%")

        if min_rating is not None:
            query += """
            AND b.rating >= %s
            """

            params.append(min_rating)

        if tag:
            # Tags are stored as an array, so convert to text for a simple
            # case-insensitive partial match.
            query += """
            AND array_to_string(
                b.tags,
                ','
            ) ILIKE %s
            """

            params.append(
                f"%{tag}%"
            )

        if published_year is not None:
            query += """
            AND EXTRACT(YEAR FROM b.publish_date) = %s
            """

            params.append(published_year)

        if published_before_year is not None:
            query += """
            AND b.publish_date < make_date(%s, 1, 1)
            """

            params.append(published_before_year)

        if published_after_year is not None:
            query += """
            AND b.publish_date >= make_date(%s, 1, 1)
            """

            params.append(published_after_year)

        offset = (page - 1) * limit

        query += """
        GROUP BY b.work_key,
                 b.title,
                 b.tags,
                 b.publish_date,
                 b.rating,
                 b.cover_id

        LIMIT %s
        OFFSET %s
        """

        params.append(limit)
        params.append(offset)

        cursor.execute(
            query,
            params
        )

        books = cursor.fetchall()

        set_json(
            cache_key,
            books,
            ttl_seconds=BOOK_SEARCH_CACHE_TTL_SECONDS
        )

        return books

    finally:

        cursor.close()


def get_top_rated_books_by_tag(
        tag: str,
        limit: int = 5,
        conn=None
):
    """Return the highest-rated books that share a specific tag."""

    if limit < 1:
        limit = 5

    if limit > 20:
        limit = 20

    cache_key = make_cache_key(
        "book:top_by_tag",
        {
            "tag": tag,
            "limit": limit
        }
    )

    cached_books = get_json(cache_key)

    if cached_books is not None:
        return cached_books

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:

        query = """
                SELECT b.work_key,
                       b.title,
                       b.tags,
                       b.publish_date,
                       b.rating,
                       b.cover_id,
                       COALESCE(
                           ARRAY_AGG(a.author_name)
                           FILTER (WHERE a.author_name IS NOT NULL),
                           ARRAY[]::text[]
                       ) AS authors

                FROM books b

                         LEFT JOIN book_authors ba
                               ON b.work_key = ba.work_key

                         LEFT JOIN authors a
                               ON ba.author_key = a.author_key

                WHERE EXISTS (
                    SELECT 1
                    FROM unnest(COALESCE(b.tags, ARRAY[]::text[])) AS book_tag
                    WHERE BTRIM(book_tag) ILIKE %s
                )

                GROUP BY b.work_key,
                         b.title,
                         b.tags,
                         b.publish_date,
                         b.rating,
                         b.cover_id

                ORDER BY b.rating DESC NULLS LAST,
                         b.title ASC

                LIMIT %s
                """

        cursor.execute(
            query,
            (
                tag.strip(),
                limit
            )
        )

        books = cursor.fetchall()

        set_json(
            cache_key,
            books,
            ttl_seconds=BOOK_TAG_CACHE_TTL_SECONDS
        )

        return books

    finally:

        cursor.close()


def recommend_books(
        prompt: str,
        concept_groups: list[str] | None = None,
        limit: int = 10,
        conn=None
):
    """Rank books by matching expanded concept groups against local metadata."""

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:

        prepared_groups = build_recommendation_groups(
            prompt,
            concept_groups
        )

        concept_count = len(prepared_groups)

        if limit < 1:
            limit = 10

        if limit > 20:
            limit = 20

        cache_key = make_cache_key(
            "book:recommend",
            {
                "prepared_groups": prepared_groups,
                "concept_count": concept_count,
                "limit": limit
            }
        )

        cached_books = get_json(cache_key)

        if cached_books is not None:
            return cached_books

        # The CTE pipeline keeps this readable:
        # recommendation_groups turns JSON input into SQL rows,
        # candidate_books builds one row per book with authors,
        # scored_books calculates group coverage and weighted term matches.
        query = """
                WITH recommendation_groups AS (
                    SELECT (group_data ->> 'group_id')::int AS group_id,
                           ARRAY(
                               SELECT jsonb_array_elements_text(group_data -> 'terms')
                           ) AS terms
                    FROM jsonb_array_elements(%s::jsonb) AS groups(group_data)
                ),
                candidate_books AS (
                    SELECT b.work_key,
                           b.title,
                           b.tags,
                           b.publish_date,
                           b.rating,
                           b.cover_id,
                           COALESCE(
                               ARRAY_AGG(a.author_name)
                               FILTER (WHERE a.author_name IS NOT NULL),
                               ARRAY[]::text[]
                           ) AS authors

                    FROM books b

                             LEFT JOIN book_authors ba
                                   ON b.work_key = ba.work_key

                             LEFT JOIN authors a
                                   ON ba.author_key = a.author_key

                    GROUP BY b.work_key,
                             b.title,
                             b.tags,
                             b.publish_date,
                             b.rating,
                             b.cover_id
                ),
                scored_books AS (
                    SELECT c.work_key,
                           c.title,
                           c.tags,
                           c.publish_date,
                           c.rating,
                           c.cover_id,
                           c.authors,
                           (
                               SELECT COUNT(*)
                               FROM recommendation_groups rg
                               WHERE EXISTS (
                                   SELECT 1
                                   FROM unnest(rg.terms) AS term
                                   WHERE c.title ILIKE '%%' || term || '%%'
                                      OR EXISTS (
                                          SELECT 1
                                          FROM unnest(COALESCE(c.tags, ARRAY[]::text[])) AS tag
                                          WHERE tag ILIKE '%%' || term || '%%'
                                      )
                                      OR EXISTS (
                                          SELECT 1
                                          FROM unnest(COALESCE(c.authors, ARRAY[]::text[])) AS author
                                          WHERE author ILIKE '%%' || term || '%%'
                                      )
                               )
                           ) AS matched_concept_count,
                           (
                               SELECT COALESCE(SUM(
                                   (
                                       SELECT COUNT(*)
                                       FROM unnest(rg.terms) AS term
                                       WHERE c.title ILIKE '%%' || term || '%%'
                                   ) * 4
                                   +
                                   (
                                       SELECT COUNT(*)
                                       FROM unnest(rg.terms) AS term
                                       WHERE EXISTS (
                                           SELECT 1
                                           FROM unnest(COALESCE(c.tags, ARRAY[]::text[])) AS tag
                                           WHERE tag ILIKE '%%' || term || '%%'
                                       )
                                   ) * 3
                                   +
                                   (
                                       SELECT COUNT(*)
                                       FROM unnest(rg.terms) AS term
                                       WHERE EXISTS (
                                           SELECT 1
                                           FROM unnest(COALESCE(c.authors, ARRAY[]::text[])) AS author
                                           WHERE author ILIKE '%%' || term || '%%'
                                       )
                                   ) * 2
                               ), 0)
                               FROM recommendation_groups rg
                           ) AS term_score
                    FROM candidate_books c
                )
                SELECT s.work_key,
                       s.title,
                       s.tags,
                       s.publish_date,
                       s.rating,
                       s.cover_id,
                       s.authors,
                       s.matched_concept_count,
                       %s AS concept_count,
                       (
                           s.matched_concept_count * 10
                           + s.term_score
                           + COALESCE(s.rating, 0) / 5.0
                       ) AS recommendation_score

                FROM scored_books s

                WHERE s.matched_concept_count > 0

                ORDER BY s.matched_concept_count DESC,
                         recommendation_score DESC,
                         s.rating DESC NULLS LAST,
                         s.title ASC

                LIMIT %s
                """

        cursor.execute(
            query,
            (
                Json(prepared_groups),
                concept_count,
                limit
            )
        )

        books = cursor.fetchall()

        set_json(
            cache_key,
            books,
            ttl_seconds=BOOK_RECOMMENDATION_CACHE_TTL_SECONDS
        )

        return books

    finally:

        cursor.close()


def semantic_search_books(
        query: str,
        limit: int = 10,
        conn=None
):
    """Search by vector similarity using pgvector embeddings."""

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:

        if limit < 1:
            limit = 10

        if limit > 20:
            limit = 20

        cache_key = make_cache_key(
            "book:semantic",
            {
                "query": query,
                "limit": limit
            }
        )

        cached_books = get_json(cache_key)

        if cached_books is not None:
            return cached_books

        # Convert the natural-language query into a pgvector literal.
        query_embedding = format_vector(embed_text(query))

        sql = """
              SELECT b.work_key,
                     b.title,
                     b.tags,
                     b.publish_date,
                     b.rating,
                     b.cover_id,
                     COALESCE(
                         ARRAY_AGG(a.author_name)
                         FILTER (WHERE a.author_name IS NOT NULL),
                         ARRAY[]::text[]
                     ) AS authors,
                     1 - (b.embedding <=> %s::vector) AS semantic_score

              FROM books b

                       LEFT JOIN book_authors ba
                             ON b.work_key = ba.work_key

                       LEFT JOIN authors a
                             ON ba.author_key = a.author_key

              WHERE b.embedding IS NOT NULL

              GROUP BY b.work_key,
                       b.title,
                       b.tags,
                       b.publish_date,
                       b.rating,
                       b.cover_id,
                       b.embedding

              ORDER BY b.embedding <=> %s::vector

              LIMIT %s
              """

        cursor.execute(
            sql,
            (
                query_embedding,
                query_embedding,
                limit
            )
        )

        books = cursor.fetchall()

        set_json(
            cache_key,
            books,
            ttl_seconds=BOOK_RECOMMENDATION_CACHE_TTL_SECONDS
        )

        return books

    finally:

        cursor.close()


def hybrid_search_books(
        query: str,
        limit: int = 10,
        keyword_weight: float = 0.4,
        semantic_weight: float = 0.6,
        author: str | None = None,
        min_rating: float | None = None,
        tag: str | None = None,
        published_before_year: int | None = None,
        published_after_year: int | None = None,
        published_year: int | None = None,
        conn=None
):
    """Combine PostgreSQL full-text ranking with semantic similarity."""

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:

        if limit < 1:
            limit = 10

        if limit > 20:
            limit = 20

        if keyword_weight < 0:
            keyword_weight = 0

        if semantic_weight < 0:
            semantic_weight = 0

        cache_key = make_cache_key(
            "book:hybrid",
            {
                "query": query,
                "limit": limit,
                "keyword_weight": keyword_weight,
                "semantic_weight": semantic_weight,
                "author": author,
                "min_rating": min_rating,
                "tag": tag,
                "published_before_year": published_before_year,
                "published_after_year": published_after_year,
                "published_year": published_year
            }
        )

        cached_books = get_json(cache_key)

        if cached_books is not None:
            return cached_books

        # Optional filters are collected separately so they can be appended to
        # the SQL once while keeping parameter order predictable.
        filters = []
        filter_params = []

        if author:
            filters.append("""
                EXISTS (
                    SELECT 1
                    FROM book_authors filter_ba
                    JOIN authors filter_a
                      ON filter_ba.author_key = filter_a.author_key
                    WHERE filter_ba.work_key = b.work_key
                      AND filter_a.author_name ILIKE %s
                )
            """)
            filter_params.append(f"%{author}%")

        if min_rating is not None:
            filters.append("b.rating >= %s")
            filter_params.append(min_rating)

        if tag:
            filters.append("array_to_string(b.tags, ',') ILIKE %s")
            filter_params.append(f"%{tag}%")

        if published_year is not None:
            filters.append("EXTRACT(YEAR FROM b.publish_date) = %s")
            filter_params.append(published_year)

        if published_before_year is not None:
            filters.append("b.publish_date < make_date(%s, 1, 1)")
            filter_params.append(published_before_year)

        if published_after_year is not None:
            filters.append("b.publish_date >= make_date(%s, 1, 1)")
            filter_params.append(published_after_year)

        extra_filters = ""

        if filters:
            extra_filters = " AND " + " AND ".join(filters)

        query_embedding = format_vector(embed_text(query))

        # extra_filters is assembled from fixed SQL fragments above. User input
        # still goes through filter_params and cursor.execute parameters.
        sql = f"""
                WITH scored_books AS (
                    SELECT
                        b.work_key,
                        b.title,
                        b.tags,
                        b.publish_date,
                        b.rating,
                        b.cover_id,
                        COALESCE(
                            ARRAY_AGG(a.author_name)
                            FILTER (WHERE a.author_name IS NOT NULL),
                            ARRAY[]::text[]
                        ) AS authors,

                        COALESCE(
                            ts_rank(
                                b.search_vector,
                                websearch_to_tsquery('english', %s)
                            ),
                            0
                        ) AS raw_keyword_score,

                        CASE
                            WHEN b.embedding IS NULL THEN 0
                            ELSE 1 - (b.embedding <=> %s::vector)
                        END AS semantic_score

                    FROM books b
                    LEFT JOIN book_authors ba ON b.work_key = ba.work_key
                    LEFT JOIN authors a ON ba.author_key = a.author_key

                    WHERE (
                        b.search_vector @@ websearch_to_tsquery('english', %s)
                        OR b.embedding IS NOT NULL
                    )
                    {extra_filters}

                    GROUP BY b.work_key,
                             b.title,
                             b.tags,
                             b.publish_date,
                             b.rating,
                             b.cover_id,
                             b.embedding,
                             b.search_vector
                ),
                normalized_books AS (
                    SELECT
                        *,
                        CASE
                            WHEN raw_keyword_score <= 0 THEN 0
                            ELSE LEAST(raw_keyword_score, 1)
                        END AS keyword_score
                    FROM scored_books
                )
                SELECT
                    work_key,
                    title,
                    tags,
                    publish_date,
                    rating,
                    cover_id,
                    authors,
                    keyword_score,
                    semantic_score,
                    (
                        keyword_score * %s
                        + semantic_score * %s
                    ) AS hybrid_score
                FROM normalized_books
                ORDER BY hybrid_score DESC,
                        semantic_score DESC,
                        keyword_score DESC,
                        rating DESC NULLS LAST,
                        title ASC
                LIMIT %s
              """

        cursor.execute(
            sql,
            (
                query,
                query_embedding,
                query,
                *filter_params,
                keyword_weight,
                semantic_weight,
                limit
            )
        )

        books = cursor.fetchall()

        set_json(
            cache_key,
            books,
            ttl_seconds=BOOK_RECOMMENDATION_CACHE_TTL_SECONDS
        )

        return books

    finally:

        cursor.close()


def get_specific_book(
        work_key: str,
        conn=None
):
    """Fetch one book by OpenLibrary work key."""

    # Route parameters may arrive as "works/OL..." because FastAPI strips the
    # leading slash from path captures. Normalize before querying.
    normalized_work_key = (
        work_key
        if work_key.startswith("/")
        else f"/{work_key}"
    )

    cache_key = make_cache_key(
        "book:detail",
        {
            "work_key": normalized_work_key
        }
    )

    cached_book = get_json(cache_key)

    if cached_book is not None:
        return cached_book

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:

        query = """
                SELECT b.work_key, 
                       b.title, 
                       b.tags, 
                       b.publish_date, 
                       b.rating, 
                       b.cover_id,

                       ARRAY_AGG(a.author_name) AS authors

                FROM books b

                         JOIN book_authors ba
                              ON b.work_key = ba.work_key

                         JOIN authors a
                              ON ba.author_key = a.author_key

                WHERE b.work_key LIKE %s

                GROUP BY b.work_key, 
                         b.title, 
                         b.tags, 
                         b.publish_date, 
                         b.rating,
                         b.cover_id
                """

        cursor.execute(query, (normalized_work_key,))

        book = cursor.fetchone()

        set_json(
            cache_key,
            book,
            ttl_seconds=BOOK_DETAIL_CACHE_TTL_SECONDS
        )

        return book

    finally:
        cursor.close()


def similar_books(
        work_key: str,
        conn=None,
        limit: int = 10
):
    """Find books with similar tags, ratings, and authors."""

    if limit < 1:
        limit = 10

    if limit > 20:
        limit = 20

    cache_key = make_cache_key(
        "book:similar",
        {
            "work_key": work_key,
            "limit": limit
        }
    )

    cached_books = get_json(cache_key)

    if cached_books is not None:
        return cached_books

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # This is a metadata-based similarity score, not vector search:
        # shared tags matter most, shared authors matter next, and close
        # ratings add a small tie-breaking signal.
        query = """
                WITH target_book AS (
                    SELECT b.work_key,
                           b.title,
                           b.tags,
                           b.rating,
                           b.cover_id,
                           COALESCE(
                               ARRAY_AGG(a.author_name)
                               FILTER (WHERE a.author_name IS NOT NULL),
                               ARRAY[]::text[]
                           ) AS authors
                    FROM books b
                             LEFT JOIN book_authors ba
                                  ON b.work_key = ba.work_key
                             LEFT JOIN authors a
                                  ON ba.author_key = a.author_key
                    WHERE b.work_key = %s
                    GROUP BY b.work_key,
                             b.title,
                             b.tags,
                             b.rating,
                             b.cover_id
                ),
                candidate_books AS (
                    SELECT b.work_key,
                           b.title,
                           b.tags,
                           b.publish_date,
                           b.rating,
                           b.cover_id,
                           COALESCE(
                               ARRAY_AGG(a.author_name)
                               FILTER (WHERE a.author_name IS NOT NULL),
                               ARRAY[]::text[]
                           ) AS authors
                    FROM books b
                             LEFT JOIN book_authors ba
                                  ON b.work_key = ba.work_key
                             LEFT JOIN authors a
                                  ON ba.author_key = a.author_key
                    WHERE b.work_key <> %s
                    GROUP BY b.work_key,
                             b.title,
                             b.tags,
                             b.publish_date,
                             b.rating,
                             b.cover_id
                )
                SELECT c.work_key,
                       c.title,
                       c.tags,
                       c.publish_date,
                       c.rating,
                       c.cover_id,
                       c.authors,
                       (
                           COALESCE(
                               (
                                   SELECT COUNT(*)
                                   FROM unnest(COALESCE(c.tags, ARRAY[]::text[])) AS candidate_tag
                                   WHERE candidate_tag = ANY(COALESCE(t.tags, ARRAY[]::text[]))
                               ),
                               0
                           ) * 3
                           + (1 - (ABS(COALESCE(c.rating, 0) - COALESCE(t.rating, 0)) / 5.0))
                           + CASE
                               WHEN EXISTS (
                                   SELECT 1
                                   FROM unnest(COALESCE(c.authors, ARRAY[]::text[])) AS candidate_author
                                   WHERE candidate_author = ANY(COALESCE(t.authors, ARRAY[]::text[]))
                               ) THEN 2
                               ELSE 0
                             END
                       ) AS similarity_score
                FROM candidate_books c
                         CROSS JOIN target_book t
                ORDER BY similarity_score DESC,
                         c.rating DESC,
                         c.title ASC
                LIMIT %s
                """

        cursor.execute(query, (work_key, work_key, limit))

        books = cursor.fetchall()

        set_json(
            cache_key,
            books,
            ttl_seconds=BOOK_RECOMMENDATION_CACHE_TTL_SECONDS
        )

        return books

    finally:
        cursor.close()
        
