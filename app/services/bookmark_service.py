from psycopg2.extras import RealDictCursor

def save_bookmark_service(
        user_id: int,
        work_key: str,
        conn=None
):
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:

        query = """ 
                INSERT INTO bookmarks 
                    (user_id, work_key) 

                VALUES (%s, %s) 
              """

        cursor.execute(query, (user_id, work_key))

        conn.commit()  # Prevent changes disappeared

        return {"message": "Bookmark saved"}

    except Exception:

        conn.rollback()

        raise

    finally:

        cursor.close()


def get_bookmark_service(
        user_id: int,
        conn = None
):
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        query = """
                SELECT b.work_key, 
                       b.title, 
                       b.tags, 
                       b.publish_date, 
                       b.rating

                FROM bookmarks bm

                         JOIN books b
                              ON bm.work_key = b.work_key

                WHERE bm.user_id = %s 
                """

        cursor.execute(query, (user_id,))

        bookmarks = cursor.fetchall()

        return bookmarks

    finally:
        cursor.close()


def delete_bookmark_service(
        work_key: str,
        user_id: int,
        conn=None
):
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:

        query = """
                DELETE 
                FROM bookmarks

                WHERE user_id = %s
                  AND work_key = %s 
                """

        cursor.execute(query, (user_id, work_key))

        conn.commit()

        return {"message": "Bookmark deleted"}

    finally:
        cursor.close()