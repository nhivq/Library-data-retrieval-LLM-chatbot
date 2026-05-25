from fastapi import (
    FastAPI,
    APIRouter,
    Query,
    HTTPException,
    Depends
)
from psycopg2.extras import RealDictCursor
from app.database.connection import get_db
from app.schemas.schemas import RegisterRequest, LoginRequest,Bookmark
from app.routes.books import router as books_router
from app.routes.bookmarks import router as bookmarks_router
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

app.include_router(
    books_router
)

app.include_router(
    bookmarks_router
)

# Fix CORS issue
app.add_middleware(
    CORSMiddleware,

    allow_origins=["*"],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"]
)

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



