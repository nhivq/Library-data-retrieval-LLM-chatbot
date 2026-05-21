# Response/request models

from pydantic import BaseModel
from typing import List
from datetime import date

# ---------- Request Models ----------

# Expected request body for POST /bookmarks
class Bookmark(BaseModel):

    user_id: int
    work_key: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


# ---------- Response Models ( how API sends data ) ----------

class BookResponse(BaseModel):

    work_key: str
    title: str
    tags: list[str] | None = None
    publish_date: date | None = None
    rating: float | None = None
    authors: list[str] = []