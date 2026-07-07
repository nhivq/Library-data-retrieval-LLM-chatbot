from fastapi import (
    APIRouter,
    HTTPException,
    Depends
)
from app.database.connection import get_db
from app.schemas.author_schemas import AuthorResponse
from app.services import author_service


router=APIRouter(
    prefix="/authors",
    tags=["Authors"]
)


@router.get("/", response_model=list[AuthorResponse])
def get_authors(
        page: int = 1,
        limit: int = 10,
        conn=Depends(get_db)
):
    """Paginated author list."""

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


@router.get("/search")
def search_authors(
        author_name: str | None = None,
        author_key: str | None = None,
        conn=Depends(get_db)
):
    """Search authors by partial name or author key."""

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


@router.get("/{author_key:path}")
def get_author(
        author_key: str,
        conn=Depends(get_db)
):
    """Fetch one author by key. Path capture supports slash-like keys."""

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
