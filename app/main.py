from fastapi import (
    FastAPI,
    Query,
    HTTPException,
    Depends
)
from psycopg2.extras import RealDictCursor
from fastapi.middleware.cors import CORSMiddleware
from .database import get_connection
from .schemas import (
    Bookmark,
    BookResponse,
    RegisterRequest,
    LoginRequest
)

app = FastAPI()

# Fix CORS issue
app.add_middleware(
    CORSMiddleware,

    allow_origins=["*"],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"]
)

# ---------- Database Dependency ----------
# -> Avoid conn.close() to be repeated inside every endpoint.
def get_db():

    conn = get_connection()

    try:
        yield conn

    finally:
        conn.close()


# ---------- Register account ----------
@app.post("/register")
def register(user: RegisterRequest,
             conn=Depends(get_db)
):

    cursor=conn.cursor()

    try:

        query="""
        INSERT INTO users
        (username, email, password)

        VALUES(%s,%s,%s)
        """

        cursor.execute(
            query,
            (
                user.username,
                user.email,
                user.password
            )
        )

        conn.commit()

        return {
            "message":"User registered"
        }

    except Exception as e:

        conn.rollback()

        print(e)

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    finally:

        cursor.close()


# ---------- User Login ----------
@app.post("/login")
def login(user: LoginRequest,
          conn=Depends(get_db)
):

    cursor=conn.cursor(cursor_factory=RealDictCursor)

    try:

        query="""
        SELECT *
        FROM users
        WHERE username=%s
        """

        cursor.execute(query, (user.username,))

        existing_user=cursor.fetchone()

        if existing_user is None:

            raise HTTPException(
                status_code=404,
                detail="User not found"
            )


        if existing_user["password"] != user.password:

            raise HTTPException(
                status_code=401,
                detail="Wrong password"
            )


        return {
            "message":"Login successful",
            "user_id": existing_user["user_id"]
        }

    finally:

        cursor.close()

# ---------- Get Books ----------
# Path allows:
# /books
# /books?limit=20
@app.get(
    "/books",
    response_model=list[BookResponse]
)
def get_books(
        limit: int = Query(
            default=10,
            le=100 # limit <= 100
        ),
        conn=Depends(get_db)
):
    cursor = conn.cursor(
        cursor_factory=RealDictCursor
    )

    try:

        query = """
        SELECT *
        FROM books
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
@app.get("/books/search")
def search_books(
    q: str,
    limit: int = Query(default=10, le=100),
    conn=Depends(get_db)
):

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:

        query = """
        SELECT *
        FROM books
        WHERE title ILIKE %s
        OR
        %s = ANY(tags) 
            
        LIMIT %s
        """
        # ANY() means check whether this value exists inside the array

        cursor.execute(query, (f"%{q}%", q, limit))

        books = cursor.fetchall()

        return books

    finally:

        cursor.close()

# ---------- Get Specific Single Book ----------
# Path allows:
# /works/OL12345W (double // because work_key contains /)
@app.get(
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
        SELECT
            b.work_key,
            b.title,
            b.tags,
            b.publish_date,
            b.rating,
            
            ARRAY_AGG(a.author_name) AS authors
    
        FROM books b
    
        JOIN book_authors ba
        ON b.work_key=ba.work_key
    
        JOIN authors a
        ON ba.author_key=a.author_key
    
        WHERE b.work_key=%s
            
        GROUP BY
            b.work_key,
            b.title,
            b.tags,
            b.publish_date,
            b.rating
        """

        cursor.execute(query, (work_key,))

        book = cursor.fetchone() # Because 1 book can have many authors

        if not book:
            raise HTTPException(
                status_code=404,
                detail="Book not found"
            )

        return book

    finally:

            cursor.close()

# ---------- Get Author ----------
@app.get("/authors/{author_key:path}")
def get_author(author_key: str,
               conn=Depends(get_db)
):

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:

        query = """
        SELECT
            a.author_key,
            a.author_name,
    
            ARRAY_AGG(b.title) AS books
    
        FROM authors a
    
        JOIN book_authors ba
        ON a.author_key=ba.author_key
    
        JOIN books b
        ON ba.work_key=b.work_key
    
        WHERE a.author_key=%s
    
        GROUP BY
            a.author_key,
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

# ---------- Save Bookmark ----------
@app.post("/bookmarks")
def save_bookmark(bookmark: Bookmark,
                  conn=Depends(get_db)
):

    cursor=conn.cursor()

    try:

        query="""
        INSERT INTO bookmarks
        (user_id, work_key)
    
        VALUES(%s,%s)
        """

        cursor.execute(query, (bookmark.user_id, bookmark.work_key))

        conn.commit() # Prevent changes disappeared

        return {"message": "Bookmark saved"}

    except Exception: # Undo changes if error happens

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
@app.get("/bookmarks")
def get_bookmark(user_id: int,
                 conn=Depends(get_db)
):
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        query = """
        SELECT b.work_key, \
                b.title, \
                b.tags, \
                b.publish_date, \
                b.rating
    
        FROM bookmarks bm
    
        JOIN books b
        ON bm.work_key = b.work_key
    
        WHERE bm.user_id = %s \
        """

        cursor.execute(query, (user_id,))

        bookmarks = cursor.fetchall()

        return bookmarks

    finally:
        cursor.close()

# ---------- Delete Bookmarks ----------
@app.delete("/bookmarks/{work_key:path}")
def delete_bookmark(work_key: str,
                    user_id: int,
                    conn=Depends(get_db)
):

    cursor = conn.cursor()

    try:

        query = """
        DELETE FROM bookmarks
    
        WHERE
        user_id=%s
        AND
        work_key=%s
        """

        cursor.execute(query,(user_id, work_key))

        conn.commit()

        return {"message": "Bookmark deleted"}

    finally:
        cursor.close()

