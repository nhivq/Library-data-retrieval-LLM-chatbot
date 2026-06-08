from fastapi import (
    APIRouter,
    HTTPException,
    Depends
)
from app.database.connection import get_db
from app.schemas.user_schemas import RegisterRequest, LoginRequest
from app.services import auth_service 

router=APIRouter(
    tags=["Authentication"]
)

# ---------- Register account ----------
@router.post("/register")
def register(
        user: RegisterRequest,
        conn=Depends(get_db)
):
    try:

        return auth_service.register_user(
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

        return auth_service.login_user(
            username=user.username,
            password=user.password,
            conn=conn
        )


    except ValueError as e:

        raise HTTPException(

            status_code=401,

            detail=str(e)

        )
