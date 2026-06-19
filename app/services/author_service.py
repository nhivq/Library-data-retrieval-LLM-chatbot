from psycopg2.extras import RealDictCursor

def get_author(
        author_key: str,
        conn = None
):
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

        return author

    finally:
        cursor.close()


def search_authors(
        author_name: str | None = None,
        author_starts_with: str | None = None,,
        author_ends_with: str | None = None,
        author_key: str | None = None,
        conn=None
):
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

        params = []

        if author_starts_with:
            query += """
                    AND a.author_name ILIKE %s
                    """
            params.append(f"{author_starts_with}%")

        if author_ends_with:
            query += """
                    AND authors.author_name ILIKE %s
                    """
            params.append(f"{author_ends_with}")

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

        return cursor.fetchall()

    finally:
        cursor.close()


def get_authors(
        page: int = 1,
        limit: int = 10,
        conn=None
):
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        if page < 1:
            page = 1

        if limit < 1:
            limit = 10

        if limit > 100:
            limit = 100

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

        return cursor.fetchall()

    finally:
        cursor.close()
