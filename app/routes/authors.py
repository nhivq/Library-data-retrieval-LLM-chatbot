from fastapi import (
    APIRouter,
    HTTPException,
    Depends
)
from app.database.connection import get_db
from app.schemas.author_schemas import AuthorResponse
from app.services import author_service


router=APIRouter(
    tags=["Authors"]
)


# ---------- Get Authors ----------
@router.get("/authors", response_model=list[AuthorResponse])
def get_authors(
        page: int = 1,
        limit: int = 10,
        conn=Depends(get_db)
):
    try:

        return author_service.get_authors(
            page=page,
            limit=limit,
            conn=conn
        )

    except Exception:

        raise HTTPException(
            status_code=400,
            detail="Could not get authors"
        )


# ---------- Search Authors ----------
@router.get("/authors/search")
def search_authors(
        author_name: str | None = None,
        author_key: str | None = None,
        conn=Depends(get_db)
):
    try:

        return author_service.search_authors(
            author_name=author_name,
            author_key=author_key,
            conn=conn
        )

    except Exception:

        raise HTTPException(
            status_code=400,
            detail="Could not search authors"
        )


# ---------- Get Author ----------
@router.get("/authors/{author_key:path}")
def get_author(
        author_key: str,
        conn=Depends(get_db)
):
    try:

        return author_service.get_author(
            author_key=author_key,
            conn=conn
        )

    except Exception:

        raise HTTPException(
            status_code=404,
            detail="Author not found"
        )
