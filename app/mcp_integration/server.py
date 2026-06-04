from fastmcp import FastMCP
from app.database.connection import get_db
from app.schemas.bookmark_schemas import Bookmark
from app.schemas.user_schemas import LoginRequest, RegisterRequest
from app.services import author_service, book_service, bookmark_service, auth_service


# Create and name MCP server
mcp = FastMCP("Book Retrieval MCP")


# ---------- Book Tools ----------

@mcp.tool(
    description="Search books by title, author, rating and tag filters"
)
def search_books(
q: str | None = None,
        author: str | None = None,
        min_rating: float | None = None,
        tag: str | None = None,
        page:int=1,
        limit:int=10,
):

    db = get_db()
    conn = next(db)

    try:

        return book_service.search_books(
            q=q,
            author=author,
            min_rating=min_rating,
            tag=tag,
            page=page,
            limit=limit,
            conn=conn
        )

    finally:

        db.close()


@mcp.tool(
    description="Get a book by its work_key"
)
def get_book(
    work_key: str
):
    
    db = get_db()
    conn = next(db)

    try:

        return book_service.get_specific_book(
            work_key=work_key,
            conn=conn
        )
    
    finally:

        db.close()


# ---------- Author Tools ----------

@mcp.tool(
    description="Get author information by author key"
)
def get_author(
    author_key: str
):
    
    db = get_db()
    conn = next(db)

    try:

        return author_service.get_author(
            author_key=author_key,
            conn=conn
        )
    
    finally:

        db.close()


@mcp.tool(
    description="Search author by author name or author key"
)
def search_authors(
        author_name: str | None = None,
        author_key: str | None = None,
):
    
    db = get_db()
    conn = next(db)

    try:

        return author_service.search_authors(
            author_name=author_name,
            author_key=author_key,
            conn=conn
        )
    
    finally:

        db.close()


# ---------- Bookmark Tools ----------

@mcp.tool(
    description="Save book into bookmark under one's user ID"
)
def save_bookmarks(
    bookmark: Bookmark
):
    
    db = get_db()
    conn = next(db)

    try:

        return bookmark_service.save_bookmark(
            user_id=bookmark.user_id,
            work_key=bookmark.work_key,
            conn=conn
        )
    
    finally:

        db.close()


@mcp.tool(
    description="Get all bookmarks information saved under a user ID"
)
def get_bookmarks(
    user_id: int
):
    
    db = get_db()
    conn = next(db)

    try:

        return bookmark_service.get_bookmark(
            user_id=user_id,
            conn=conn
        )
    
    finally:

        db.close()


@mcp.tool(
    description="Delete specific bookmark of user"
)
def delete_bookmarks(
    work_key: str,
    user_id: int
):
    
    db = get_db()
    conn = next(db)

    try:

        return bookmark_service.delete_bookmark(
            user_id=user_id,
            work_key=work_key,
            conn=conn
        )
    
    finally:

        db.close()


# ---------- Authorization Tools ----------

@mcp.tool(
    description="Register account using email, username and password"
)
def register(
    user: RegisterRequest
):
    
    db = get_db()
    conn = next(db)

    try:

        return auth_service.register_user(
            username=user.username,
            email=user.email,
            password=user.password,
            conn=conn
        )
    
    finally:

        db.close()


@mcp.tool(
    description="Login account using username and password"
)
def login(
    user: LoginRequest
):
    
    db = get_db()
    conn = next(db)

    try:

        return auth_service.login_user(
            username=user.username,
            password=user.password,
            conn=conn
        )
    
    finally:

        db.close()


if __name__ == "__main__":
    mcp.run()
