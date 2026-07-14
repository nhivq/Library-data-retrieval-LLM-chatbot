from pydantic import BaseModel


class Bookmark(BaseModel):
    """Request body for saving a bookmark."""

    work_key: str
