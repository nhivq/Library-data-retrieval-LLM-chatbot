from fastapi import (
    APIRouter,
    HTTPException,
    Depends
)
from app.database.connection import get_db
from app.schemas.auth_schemas import RefreshRequest
from app.schemas.user_schemas import RegisterRequest, LoginRequest
from app.services import auth_service 
from app.core.dependencies import get_current_user
from app.core.security import create_access_token, decode_refresh_token


router=APIRouter(
    tags=["Authentication"]
)


@router.get("/me")
def get_me(
    user=Depends(get_current_user)
):

    return user


@router.post("/refresh")
def refresh_token(
    payload: RefreshRequest
):
    
    try:

        token_payload = decode_refresh_token(payload.refresh_token)
        
        user_id = token_payload["sub"]

        new_access_token = create_access_token(
            {"sub": user_id}
        )

        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }
    
    except Exception:

        raise HTTPException(
            status_code = 401,
            detail = "Invalid refresh token"
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
