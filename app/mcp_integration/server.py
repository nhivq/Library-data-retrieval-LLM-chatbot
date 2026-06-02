from fastmcp import FastMCP
from app.database.connection import get_db
from app.services.book_service import search_books_service

# Create and name MCP server
mcp = FastMCP("Book Retrieval MCP")

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

        return search_books_service(
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


if __name__ == "__main__":
    mcp.run()