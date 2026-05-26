from pydantic import BaseModel
from datetime import date

# ---------- Response Models ( how API sends data ) ----------
class BookResponse(BaseModel): # Inherit baseModel from pydantic for automatic validation and serialization
                            # This checks whether returned data matches expected types and converts Python object -> JSON

    work_key: str
    title: str
    tags: list[str] | None = None
    publish_date: date | None = None
    rating: float | None = None
    authors: list[str] = []
