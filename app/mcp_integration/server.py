from fastmcp import FastMCP
from app.database.connection import get_db
from app.schemas.bookmark_schemas import Bookmark
from app.schemas.user_schemas import LoginRequest, RegisterRequest
from app.services import author_service, book_service, bookmark_service, auth_service, conversation_service


# FastMCP exposes selected service functions as tools the LLM agent can call.
# Tool descriptions become model-facing instructions, so they should explain
# both when to use each tool and how to format important arguments.
mcp = FastMCP("Book Retrieval MCP")


# ---------- Book Tools ----------

@mcp.tool(
    description="""
Search books by title, author, rating, tag, and publication year filters.

Use published_before_year for requests like "before the 1980s" or
"published before 1980". Use published_after_year for requests like
"after 2000" or "since 1990". Use published_year for an exact year.

Returns matching books from the database.
"""
)
def search_books(
        q: str | None = None,
        author: str | None = None,
        min_rating: float | None = None,
        tag: str | None = None,
        published_before_year: int | None = None,
        published_after_year: int | None = None,
        published_year: int | None = None,
        page:int=1,
        limit:int=10,
):
    """MCP wrapper around strict book metadata search."""

    # get_db is a FastAPI generator dependency. Outside FastAPI, call next()
    # to get the connection and close the generator in finally.
    db = get_db()
    conn = next(db)

    try:

        return book_service.search_books(
            q=q,
            author=author,
            min_rating=min_rating,
            tag=tag,
            published_before_year=published_before_year,
            published_after_year=published_after_year,
            published_year=published_year,
            page=page,
            limit=limit,
            conn=conn
        )

    finally:

        db.close()


@mcp.tool(
    description="""
Recommend books from a natural-language taste or mood description.

Use this when the user asks for books by vibe, mood, tone, culture,
setting, theme, or a mixed request like "Japanese history with a dramatic voice".

Before calling this tool, rewrite the user's taste into a rich search prompt
with concrete related terms. Example:
User: "Japanese history with a dramatic voice"
Tool prompt: "Japanese Japan history historical culture war drama dramatic emotional literary narrative"

Also pass concept_groups as separate intent groups. Example:
["Japanese Japan", "history historical culture", "drama dramatic emotional literary narrative"]

Returns ranked recommendations from the database.
"""
)
def recommend_books(
    prompt: str,
    concept_groups: list[str] | None = None,
    limit: int = 10
):
    """MCP wrapper around concept-group recommendations."""

    db = get_db()
    conn = next(db)

    try:

        return book_service.recommend_books(
            prompt=prompt,
            concept_groups=concept_groups,
            limit=limit,
            conn=conn
        )

    finally:

        db.close()


@mcp.tool(
    description="""
Semantic vector search over book embeddings.

Use this for conceptual or natural-language queries where exact words may not
appear in the database, such as "books about friendship after war".
Returns books ranked by embedding similarity.
"""
)
def semantic_search_books(
    query: str,
    limit: int = 10
):
    """MCP wrapper around pure semantic book search."""

    db = get_db()
    conn = next(db)

    try:

        return book_service.semantic_search_books(
            query=query,
            limit=limit,
            conn=conn
        )

    finally:

        db.close()


@mcp.tool(
    description="""
Hybrid book search using both PostgreSQL keyword relevance and semantic vector similarity.

Use this for most natural-language book discovery queries, especially when the
user mixes exact terms with concepts, mood, topic, setting, or theme.
Returns books ranked by weighted keyword + semantic score.
"""
)
def hybrid_search_books(
    query: str,
    limit: int = 10,
    keyword_weight: float = 0.4,
    semantic_weight: float = 0.6
):
    """MCP wrapper around hybrid keyword/vector search."""

    db = get_db()
    conn = next(db)

    try:
        return book_service.hybrid_search_books(
            query=query,
            limit=limit,
            keyword_weight=keyword_weight,
            semantic_weight=semantic_weight,
            conn=conn
        )

    finally:
        db.close()


@mcp.tool(
    description="Get one book by its exact work_key."
)
def get_book(
    work_key: str
):
    """MCP wrapper for fetching a single book by work key."""
    
    db = get_db()
    conn = next(db)

    try:

        return book_service.get_specific_book(
            work_key=work_key,
            conn=conn
        )
    
    finally:

        db.close()


@mcp.tool(
        description= """
Find books similar to a given book by work_key.

Returns ranked books using tag overlap, rating closeness, and shared authors.
"""
)
def similar_books(
    work_key: str
):
    """MCP wrapper for metadata-based similar books."""
    
    db = get_db()
    conn = next(db)

    try:

        return book_service.similar_books(
            work_key=work_key,
            conn=conn
        )
    
    finally:

        db.close()


# ---------- Author Tools ----------

@mcp.tool(
    description="Get one author by exact author key."
)
def get_author(
    author_key: str
):
    """MCP wrapper for fetching one author."""
    
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
    description="""
    Search authors by name pattern or author key.

    author_name:
    Match authors whose names contain text.

    author_starts_with:
    Match authors whose names begin with specific letters.

    author_ends_with:
    Match authors whose names end with specific letters.

    Returns:
    - author name
    - author key
    - books written by that author
    """
)
def search_authors(
        author_name: str | None = None,
        author_starts_with: str | None = None,
        author_ends_with: str | None = None,
        author_key: str | None = None
):
    """MCP wrapper for flexible author search."""
    
    db = get_db()
    conn = next(db)

    try:

        return author_service.search_authors(
            author_name=author_name,
            author_starts_with=author_starts_with,
            author_ends_with=author_ends_with,
            author_key=author_key,
            conn=conn
        )
    
    finally:

        db.close()


# ---------- Bookmark Tools ----------

@mcp.tool(
    description="""
    Save a book bookmark.

    IMPORTANT:
    work_key must be the exact value returned by search_books.

    Valid examples:
    "/works/OL10410009W"
    "/works/OL1068669W"

    Do NOT remove the "/works/" prefix.
    Do NOT use book titles.
    Do NOT shorten the identifier.

    """
)
def save_bookmarks(
    bookmark: Bookmark,
    user_id: int
):
    """Save a bookmark on behalf of the authenticated chat user."""
    
    db = get_db()
    conn = next(db)

    try:

        return bookmark_service.save_bookmark(
            user_id=user_id,
            work_key=bookmark.work_key,
            conn=conn
        )
    
    finally:

        db.close()


@mcp.tool(
    description="Get all bookmarks saved by the current user."
)
def get_bookmarks(
    user_id: int
):
    """Return bookmarks for the authenticated chat user."""
    
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
    description="Delete one bookmark from the current user's saved books by work_key."
)
def delete_bookmarks(
    work_key: str,
    user_id: int
):
    """Delete one bookmark for the authenticated chat user."""
    
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


# ---------- Conversation Tools ----------

@mcp.tool(
    description="Delete all chat conversations for the current authenticated user."
)
def delete_all_conversations(
    user_id: int
):
    """Delete all conversations for the authenticated chat user."""

    db = get_db()
    conn = next(db)

    try:

        deleted_count = conversation_service.delete_all_conversations(
            user_id=user_id,
            conn=conn
        )

        return {
            "message": "Conversations deleted",
            "deleted_count": deleted_count
        }

    finally:

        db.close()


# ---------- Authorization Tools ----------

@mcp.tool(
    description="Register a user account with username, email, and password."
)
def register(
    user: RegisterRequest
):
    """Register a username/password account through MCP."""
    
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
    description="Login a user with username and password."
)
def login(
    user: LoginRequest
):
    """Authenticate through MCP and return JWTs."""
    
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
