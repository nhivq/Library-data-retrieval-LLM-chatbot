from pydantic import BaseModel

# ---------- Request Models ----------
class Bookmark(BaseModel):

    user_id: int
    work_key: str