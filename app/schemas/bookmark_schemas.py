from pydantic import BaseModel

# ---------- Request Models ----------
class Bookmark(BaseModel):

    work_key: str