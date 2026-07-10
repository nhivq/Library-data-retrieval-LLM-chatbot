from fastapi import (
    APIRouter,
    Query,
    HTTPException,
    Depends
)
from app.database.connection import get_db
from app.schemas.book_schemas import BookResponse, SimilarBookResponse, RecommendationBookResponse, SemanticBookResponse, HybridBookResponse
from app.services import book_service

router=APIRouter(
    prefix="/books",
    tags=["Books"]
)

@router.get(
    "/",
    response_model=list[BookResponse]
)
def get_books(
        # Query validates the request before the service layer runs.
        limit: int = Query(
            default=10,
            le=100
        ),
        # get_db owns connection cleanup for this request.
        conn=Depends(get_db)
):
    """Return a small list of books for browsing."""

    try:

        return book_service.get_books(
            limit=limit,
            conn=conn
        )

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail="Could not get books"
        )


@router.get(
    "/search",
    response_model=list[BookResponse]
)
def search_books(
        q: str | None = None,
        author: str | None = None,
        min_rating: float | None = None,
        tag: str | None = None,
        published_before_year: int | None = None,
        published_after_year: int | None = None,
        published_year: int | None = None,
        page:int=1,
        limit:int=10,
        conn=Depends(get_db)
):
    """Strict metadata search for title, author, rating, tag, and year filters."""

    try:

        return book_service.search_books(
            q=q,
            author=author,
            min_rating=min_rating,
            tag=tag,
            published_before_year=published_before_year,
            published_after_year=published_after_year,
            published_year=published_year,
            page=page,
            limit=limit,
            conn=conn
        )


    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail="Could not search books"
        )


@router.get(
    "/recommendations",
    response_model=list[RecommendationBookResponse]
)
def recommend_books(
        prompt: str,
        concept_groups: list[str] | None = Query(default=None),
        limit: int = 10,
        conn=Depends(get_db)
):
    """Recommendation endpoint for taste, mood, theme, or mixed requests."""

    try:

        return book_service.recommend_books(
            prompt=prompt,
            concept_groups=concept_groups,
            limit=limit,
            conn=conn
        )

    except Exception:

        raise HTTPException(
            status_code=400,
            detail="Could not recommend books"
        )


@router.get(
    "/top-rated-by-tag",
    response_model=list[BookResponse]
)
def top_rated_books_by_tag(
        tag: str,
        limit: int = 5,
        conn=Depends(get_db)
):
    """Return the highest-rated books that share a selected tag."""

    try:

        return book_service.get_top_rated_books_by_tag(
            tag=tag,
            limit=limit,
            conn=conn
        )

    except Exception:

        raise HTTPException(
            status_code=400,
            detail="Could not get books by tag"
        )


@router.get(
    "/semantic-search",
    response_model=list[SemanticBookResponse]
)
def semantic_search_books(
        query: str,
        limit: int = 10,
        conn=Depends(get_db)
):
    """Pure vector search endpoint for conceptual queries."""

    try:

        return book_service.semantic_search_books(
            query=query,
            limit=limit,
            conn=conn
        )

    except RuntimeError as e:

        raise HTTPException(
            status_code=503,
            detail=str(e)
        )

    except Exception:

        raise HTTPException(
            status_code=400,
            detail="Could not search books semantically"
        )
    

@router.get(
    "/hybrid-search",
    response_model=list[HybridBookResponse]
)
def hybrid_search_books(
        query: str,
        limit: int = 10,
        keyword_weight: float = 0.4,
        semantic_weight: float = 0.6,
        author: str | None = None,
        min_rating: float | None = None,
        tag: str | None = None,
        published_before_year: int | None = None,
        published_after_year: int | None = None,
        published_year: int | None = None,
        conn=Depends(get_db)
):
    """Default discovery endpoint combining keyword and vector relevance."""

    try:
        return book_service.hybrid_search_books(
            query=query,
            limit=limit,
            keyword_weight=keyword_weight,
            semantic_weight=semantic_weight,
            author=author,
            min_rating=min_rating,
            tag=tag,
            published_before_year=published_before_year,
            published_after_year=published_after_year,
            published_year=published_year,
            conn=conn
        )

    except RuntimeError as e:
        raise HTTPException(
            status_code=503,
            detail=str(e)
        )

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Could not search books with hybrid search"
        )


@router.get(
    "/{work_key:path}",
    # OpenLibrary work keys include slashes, so path captures the full key.
    response_model=BookResponse
)
def get_book(
        work_key: str,
        conn=Depends(get_db)
):

    try:

        book = book_service.get_specific_book(
            work_key=work_key,
            conn=conn
        )

        if not book:
            raise HTTPException(
                status_code=404,
                detail="Book not found"
            )

        return book
    except HTTPException:

        raise

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail="Could not retrieve book"
        )


@router.get(
    "/{work_key:path}/similar",
    response_model=list[SimilarBookResponse]
)
def similar_books(
    work_key: str,
    conn=Depends(get_db)
):
    """Return metadata-similar books for a given OpenLibrary work key."""

    
    try:
    
        return book_service.similar_books(
            work_key,
            conn
        )
    
    except HTTPException:

        raise

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail="Could not find similar books"
        )
