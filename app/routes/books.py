from fastapi import (
    APIRouter,
    Query,
    HTTPException,
    Depends
)
from psycopg2.extras import RealDictCursor
from app.database.connection import get_db
from app.schemas.book_schemas import BookResponse

router=APIRouter()

# ---------- Get Books ----------
# Path allows:
# /books
# /books?limit=20
@router.get(
    "/books",
    response_model=list[BookResponse]
)
def get_books(
        limit: int = Query(
            default=10,
            le=100  # limit <= 100
        ),
        conn=Depends(get_db)
):
    cursor = conn.cursor(
        cursor_factory=RealDictCursor
    )

    try:

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

        cursor.execute(query, (limit,))

        books = cursor.fetchall()

        return books

    finally:

        cursor.close()


# ---------- Search Books ----------
# Path allows:
# /books/search?q=history
@router.get(
    "/books/search",
    response_model=list[BookResponse]
)
def search_books(
        q: str | None = None,
        author: str | None = None,
        min_rating: float | None = None,
        tag: str | None = None,
        page:int=1,
        limit:int=10,
        conn=Depends(get_db)
):
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:

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
            query += """
                AND b.title ~* %s
                """

            params.append(
                fr"\m{q}\M"
            )

        if author:
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

        if tag:
            query += """
            AND array_to_string(
                b.tags,
                ','
            ) ILIKE %s
            """

            params.append(
                f"%{tag}%"
            )

        if page < 1:
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


    except Exception as e:

        print(e)

        raise HTTPException(
            status_code=400,
            detail="Could not search books"
        )

    finally:

        cursor.close()


# ---------- Get Specific Single Book ----------
# Path allows:
# /works/OL12345W (double // because work_key contains /)
@router.get(
    "/books/{work_key:path}",
    response_model=BookResponse
)
def get_book(
        work_key: str,
        conn=Depends(get_db)
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

                WHERE b.work_key = %s

                GROUP BY b.work_key, 
                         b.title, 
                         b.tags, 
                         b.publish_date, 
                         b.rating 
                """

        cursor.execute(query, (work_key,))

        book = cursor.fetchone()  # Because 1 book can have many authors

        if not book:
            raise HTTPException(
                status_code=404,
                detail="Book not found"
            )

        return book

    finally:

        cursor.close()


# ---------- Get Author ----------
@router.get("/authors/{author_key:path}")
def get_author(author_key: str,
               conn=Depends(get_db)
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

        if not author:
            raise HTTPException(
                status_code=404,
                detail="Author not found"
            )

        return author

    finally:

        cursor.close()
