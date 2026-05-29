from fastapi import (
    APIRouter,
    Query,
    HTTPException,
    Depends
)
from app.database.connection import get_db
from app.schemas.book_schemas import BookResponse
from app.services.book_service import search_books_service
from app.services.book_service import get_specific_book_service
from app.services.book_service import get_books_service

router=APIRouter()

# ---------- Get Books ----------
# Path allows:
# /books
# /books?limit=20
@router.get(
    "/books",
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

        return get_books_service(
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
    "/books/search",
    response_model=list[BookResponse] # dùng list vì /books returns multiple books
)
def search_books(
        q: str | None = None,
        author: str | None = None,
        min_rating: float | None = None,
        tag: str | None = None,
        page:int=1,
        limit:int=10,
        conn=Depends(get_db)
):
    try:

        return search_books_service(
            q=q,
            author=author,
            min_rating=min_rating,
            tag=tag,
            page=page,
            limit=limit,
            conn=conn
        )


    except Exception as e:

        print(e)

        raise HTTPException(  # Standardize API behaviour
            status_code=400, # Return proper HTTP status codes & meaningful error messages
            detail="Could not search books"
        )


# ---------- Get Specific Single Book ----------
# Path allows:
# /works/OL12345W (double // because work_key contains /)
@router.get(
    "/books/{work_key:path}",
    response_model=BookResponse # response_model validates API responses & ensures the returned data follows a structure
)                               # If it is removed -> May return wrong fields/ unexpected data
def get_book(
        work_key: str,
        conn=Depends(get_db)
):

    try:

        book = get_specific_book_service(
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