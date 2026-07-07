import re
from psycopg2.extras import Json, RealDictCursor # By default, psycopg2 returns tuples
from app.semantic.embeddings import embed_text, format_vector


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

# display first n books
def get_books(
        limit: int = 10,
        conn=None
):
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try: # "try" allow handling exceptions without crashing the application

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

        cursor.execute(query, (limit,)) # Parameterized query to prevent SQL Injection and separate SQL logic from user input

        books = cursor.fetchall()

        return books

    finally: # Make sure là kể cả lỗi hay 0 thì luôn cleanup

        cursor.close()


def search_books(
        q: str | None = None, # None = None -> this is optional, allow request without this parameter required
        author: str | None = None,
        min_rating: float | None = None,
        tag: str | None = None,
        published_before_year: int | None = None,
        published_after_year: int | None = None,
        published_year: int | None = None,
        page:int=1, # with nothing behind, this is mandatory -> without it, fail validation
        limit:int=10,
        conn = None # Used if caller provides connection; otherwise, do nothing
):
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:

        # COALESCE returns first non-null value, replaces all null values with []
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
            # ~* dùng tương tự như ILIKE nhưng sẽ tránh đc i: art; o: cartoon
            query += """
                AND b.title ~* %s 
                """

            params.append(
                fr"\m{q}\M"
            )

        if author:
            # EXISTS: I only need to know whether matching rows exist
            # SELECT 1: I don't care what data is in it -> it could be any numbers but normally 1 is used
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

        if tag: # ILIKE = case-insensitive matching; LIKE = case-sensitive
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

        if page < 1: # manually validate; query validation isn't used in this case for simplicity
            page = 1

        if limit < 1:
            limit = 10

        if limit > 100:
            limit = 100

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
        return books

    finally:

        cursor.close()


def recommend_books(
        prompt: str,
        concept_groups: list[str] | None = None,
        limit: int = 10,
        conn=None
):
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

        return cursor.fetchall()

    finally:

        cursor.close()


def semantic_search_books(
        query: str,
        limit: int = 10,
        conn=None
):
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:

        if limit < 1:
            limit = 10

        if limit > 20:
            limit = 20

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

        return cursor.fetchall()

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

        return cursor.fetchall()

    finally:

        cursor.close()


def get_specific_book(
        work_key: str,
        conn=None
):
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    normalized_work_key = (
        work_key
        if work_key.startswith("/")
        else f"/{work_key}"
    )

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

        book = cursor.fetchone()  # Because 1 book can have many authors

        return book

    finally:
        cursor.close()


def similar_books(
        work_key: str,
        conn=None,
        limit: int = 10
):
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
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

        return cursor.fetchall()

    finally:
        cursor.close()
        
