from fastmcp import FastMCP
from app.database.connection import get_db
from app.services import author_service, book_service

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


@mcp.tool(
    description="Get author information by author_key"
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


if __name__ == "__main__":
    mcp.run()
