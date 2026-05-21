# Response/request models

from pydantic import BaseModel
from typing import List
from datetime import date

# ---------- Request Models ----------

# Expected request body for POST /bookmarks
class Bookmark(BaseModel):

    user_id: int
    work_key: str


# ---------- Response Models ( how API sends data ) ----------

class BookResponse(BaseModel):

    work_key: str
    title: str
    tags: list[str] | None = None
    publish_date: date | None = None
    rating: float | None = None
    authors: list[str] = []


class BookDetailResponse(BookResponse):

    authors: list[str]


class BookmarkResponse(BookResponse):
    pass


class AuthorResponse(BaseModel):

    author_key: str
    author_name: str
    books: list[str]