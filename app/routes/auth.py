from fastapi import (
    APIRouter,
    HTTPException,
    Depends
)
from app.database.connection import get_db
from app.schemas.user_schemas import RegisterRequest, LoginRequest
from app.services.auth_service import register_user_service
from app.services.auth_service import login_service

router=APIRouter()

# ---------- Register account ----------
@router.post("/register")
def register(
        user: RegisterRequest,
        conn=Depends(get_db)
):
    try:

        return register_user_service(
            username=user.username,
            email=user.email,
            password=user.password,
            conn=conn
        )

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Could not register user"
        )


# ---------- User Login ----------
@router.post("/login")
def login(
        user: LoginRequest,
        conn=Depends(get_db)
):
    try:

        return login_service(
            username=user.username,
            password=user.password,
            conn=conn
        )


    except ValueError as e:

        raise HTTPException(

            status_code=401,

            detail=str(e)

        )