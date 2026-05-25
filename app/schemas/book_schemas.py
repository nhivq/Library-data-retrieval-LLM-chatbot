from pydantic import BaseModel
from datetime import date

# ---------- Response Models ( how API sends data ) ----------
class BookResponse(BaseModel):

    work_key: str
    title: str
    tags: list[str] | None = None
    publish_date: date | None = None
    rating: float | None = None
    authors: list[str] = []
