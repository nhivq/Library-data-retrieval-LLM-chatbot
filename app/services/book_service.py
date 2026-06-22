from psycopg2.extras import RealDictCursor # By default, psycopg2 returns tuples

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
                         b.rating

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

            params.append(
                f"%{author}%"
            )

        if min_rating is not None:
            query += """
            AND b.rating >= %s
            """

            params.append(
                min_rating
            )

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
                 b.rating

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


def get_specific_book(
        work_key: str,
        conn=None
):
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:

        query = """
                SELECT b.work_key, 
                       b.title, 
                       b.tags, 
                       b.publish_date, 
                       b.rating, 

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
                         b.rating 
                """

        cursor.execute(query, (work_key,))

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
                             b.rating
                ),
                candidate_books AS (
                    SELECT b.work_key,
                           b.title,
                           b.tags,
                           b.publish_date,
                           b.rating,
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
                             b.rating
                )
                SELECT c.work_key,
                       c.title,
                       c.tags,
                       c.publish_date,
                       c.rating,
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
        
