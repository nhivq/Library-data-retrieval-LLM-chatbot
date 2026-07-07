from pydantic import BaseModel


class AuthorResponse(BaseModel):
    """Author response with the titles linked through book_authors."""

    author_key: str
    author_name: str
    books: list[str] = []
