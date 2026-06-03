from fastapi import (
    APIRouter,
    HTTPException,
    Depends
)
from app.database.connection import get_db
from app.services.author_service import get_author

router=APIRouter()

# ---------- Get Author ----------
@router.get("/authors/{author_key:path}")
def get_author(
        author_key: str,
        conn=Depends(get_db)
):
    try:

        return get_author(
            author_key=author_key,
            conn=conn
        )

    except Exception:

        raise HTTPException(
            status_code=404,
            detail="Author not found"
        )
