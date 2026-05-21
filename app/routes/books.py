from fastapi import APIRouter
from app.database import get_connection
from psycopg2.extras import RealDictCursor

router = APIRouter()

@router.get("/books")
def get_books():
    conn = get_connection()
    cursor = conn.cursor(
        cursor_factory=RealDictCursor
    )
    cursor.execute("""
        SELECT *
        FROM books
        LIMIT 10
    """)
    books = cursor.fetchall()
    cursor.close()
    conn.close()
    return books