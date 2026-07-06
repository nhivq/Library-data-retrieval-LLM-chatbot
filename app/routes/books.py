from fastapi import (
    APIRouter,
    Query,
    HTTPException,
    Depends
)
from app.database.connection import get_db
from app.schemas.book_schemas import BookResponse, SimilarBookResponse, RecommendationBookResponse, SemanticBookResponse
from app.services import book_service

router=APIRouter(
    prefix="/books",
    tags=["Books"]
)

# ---------- Get Books ----------
# Path allows:
# /books
# /books?limit=20
@router.get(
    "/",
    response_model=list[BookResponse]
)
def get_books(
        limit: int = Query( # Query() allows additional validation and metadata
            default=10,
            le=100  # limit <= 100
        ),
        conn=Depends(get_db) # avoid repeating db connection code in every endpoint -> easier to maintain
):
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


# ---------- Search Books ----------
# Path allows:
# /books/search?q=history
@router.get(
    "/search",
    response_model=list[BookResponse] # dùng list vì /books returns multiple books
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

        raise HTTPException(  # Standardize API behaviour
            status_code=400, # Return proper HTTP status codes & meaningful error messages
            detail="Could not search books"
        )


# ---------- Recommend Books ----------
# Path allows:
# /books/recommendations?prompt=japanese history drama voice
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


# ---------- Semantic Search Books ----------
# Path allows:
# /books/semantic-search?query=friendship after war
@router.get(
    "/semantic-search",
    response_model=list[SemanticBookResponse]
)
def semantic_search_books(
        query: str,
        limit: int = 10,
        conn=Depends(get_db)
):
    try:

        return book_service.semantic_search_books(
            query=query,
            limit=limit,
            conn=conn
        )

    except Exception:

        raise HTTPException(
            status_code=400,
            detail="Could not search books semantically"
        )


# ---------- Get Specific Single Book ----------
# Path allows:
# /works/OL12345W (double // because work_key contains /)
@router.get(
    "/{work_key:path}",
    response_model=BookResponse # response_model validates API responses & ensures the returned data follows a structure
)                               # If it is removed -> May return wrong fields/ unexpected data
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


# ---------- Find Similar Books ----------
# Path allows:
# /books/{work_key}/similar
@router.get(
    "/{work_key:path}/similar",
    response_model=list[SimilarBookResponse]
)
def similar_books(
    work_key: str,
    conn=Depends(get_db)
):
    
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
