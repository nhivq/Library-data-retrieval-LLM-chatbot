from psycopg2.extras import RealDictCursor

def get_author_service(
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

                         JOIN book_authors ba
                              ON a.author_key = ba.author_key

                         JOIN books b
                              ON ba.work_key = b.work_key

                WHERE a.author_key = %s

                GROUP BY a.author_key, 
                         a.author_name 
                """

        cursor.execute(query, (author_key,))

        author = cursor.fetchone()

        return author

    finally:
        cursor.close()