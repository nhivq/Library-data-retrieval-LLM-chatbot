from fastapi import (
    APIRouter,
    HTTPException,
    Depends
)
from app.database.connection import get_db
from app.schemas.bookmark_schemas import Bookmark
from app.services.bookmark_service import get_bookmark
from app.services.bookmark_service import save_bookmark
from app.services.bookmark_service import delete_bookmark

router=APIRouter()

# ---------- Save Bookmark ----------
@router.post("/bookmarks")
def save_bookmark(
        bookmark: Bookmark,
        conn=Depends(get_db)
):
    try:

        return save_bookmark(
            user_id=bookmark.user_id,
            work_key=bookmark.work_key,
            conn=conn
        )

    except Exception:  # Undo changes if error happens

        raise HTTPException(
            status_code=400,
            detail="Could not save bookmark"
        )


# ---------- Get Bookmarks ----------
# Path allows:
# /bookmarks?user_id=1
@router.get("/bookmarks")
def get_bookmark(
        user_id: int,
        conn=Depends(get_db)
):
    try:

        return get_bookmark(
            user_id=user_id,
            conn=conn
        )

    except Exception as e:
        print(e)

        raise HTTPException(
            status_code=404,
            detail="Bookmark not found"
        )


# ---------- Delete Bookmarks ----------
@router.delete("/bookmarks/{work_key:path}")
def delete_bookmark(
        work_key: str,
        user_id: int,
        conn=Depends(get_db)
):
    cursor = conn.cursor()

    try:

        return delete_bookmark(
            user_id=user_id,
            work_key=work_key,
            conn=conn
        )

    except Exception:  # Undo changes if error happens

        raise HTTPException(
            status_code=400,
            detail="Could not delete bookmark"
        )
