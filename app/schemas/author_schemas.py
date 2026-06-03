from pydantic import BaseModel


class AuthorResponse(BaseModel):
    author_key: str
    author_name: str
    books: list[str] = []
