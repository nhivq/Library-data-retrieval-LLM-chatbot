from fastapi import (
    APIRouter,
    HTTPException,
    Depends
)
from app.database.connection import get_db
from app.schemas.bookmark_schemas import Bookmark
from app.services import bookmark_service
from app.core.dependencies import get_current_user

router=APIRouter(
    prefix="/bookmarks",
    tags=["Bookmarks"]
)

@router.post("/")
def save_bookmark(
        bookmark: Bookmark,
        user=Depends(get_current_user),
        conn=Depends(get_db)
):
    """Save a bookmark for the authenticated user."""

    try:

        return bookmark_service.save_bookmark(
            user_id=user["user_id"],
            work_key=bookmark.work_key,
            conn=conn
        )

    except Exception:

        raise HTTPException(
            status_code=400,
            detail="Could not save bookmark"
        )


@router.get("/")
def get_bookmark(
        user=Depends(get_current_user),
        conn=Depends(get_db)
):
    """Return bookmarks for the authenticated user only."""

    try:

        return bookmark_service.get_bookmark(
            user_id=user["user_id"],
            conn=conn
        )

    except Exception as e:
        print(e)

        raise HTTPException(
            status_code=404,
            detail="Bookmark not found"
        )


@router.delete("/{work_key:path}")
def delete_bookmark(
        work_key: str,
        user=Depends(get_current_user),
        conn=Depends(get_db)
):
    """Delete one bookmark for the authenticated user.

    work_key uses the path converter because OpenLibrary keys contain slashes.
    """

    try:

        return bookmark_service.delete_bookmark(
            user_id=user["user_id"],
            work_key=work_key,
            conn=conn
        )

    except Exception:

        raise HTTPException(
            status_code=400,
            detail="Could not delete bookmark"
        )
