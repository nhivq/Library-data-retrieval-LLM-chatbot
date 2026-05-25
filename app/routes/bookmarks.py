from fastapi import (
    APIRouter,
    Query,
    HTTPException,
    Depends
)
from psycopg2.extras import RealDictCursor
from app.database.connection import get_db
from app.schemas.bookmark_schemas import Bookmark

router=APIRouter()

# ---------- Save Bookmark ----------
@router.post("/bookmarks")
def save_bookmark(bookmark: Bookmark,
                  conn=Depends(get_db)
                  ):
    cursor = conn.cursor()

    try:

        query = """ 
                INSERT INTO bookmarks 
                    (user_id, work_key) 

                VALUES (%s, %s) 
              """

        cursor.execute(query, (bookmark.user_id, bookmark.work_key))

        conn.commit()  # Prevent changes disappeared

        return {"message": "Bookmark saved"}

    except Exception:  # Undo changes if error happens

        conn.rollback()

        raise HTTPException(
            status_code=400,
            detail="Could not save bookmark"
        )

    finally:

        cursor.close()


# ---------- Get Bookmarks ----------
# Path allows:
# /bookmarks?user_id=1
@router.get("/bookmarks")
def get_bookmark(user_id: int,
                 conn=Depends(get_db)
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


# ---------- Delete Bookmarks ----------
@router.delete("/bookmarks/{work_key:path}")
def delete_bookmark(work_key: str,
                    user_id: int,
                    conn=Depends(get_db)
                    ):
    cursor = conn.cursor()

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