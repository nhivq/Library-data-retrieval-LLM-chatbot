from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    Request
)
from authlib.integrations.starlette_client import OAuth
from fastapi.responses import RedirectResponse

from app.database.connection import get_db
from app.schemas.auth_schemas import RefreshRequest
from app.schemas.user_schemas import RegisterRequest, LoginRequest
from app.services import auth_service 
from app.core.dependencies import get_current_user
from app.core.security import create_access_token, decode_refresh_token, create_refresh_token
from app.core.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI, FRONTEND_URL
from app.services import oauth_service


router=APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


# ---------- OAuth Object ----------
oauth = OAuth()


oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"}
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


# ---------- OAuth Login----------
@router.get("/google")
async def google_login(
    request: Request
):
    
    redirect_uri = GOOGLE_REDIRECT_URI

    return await oauth.google.authorize_redirect(
        request,
        redirect_uri
    )


# ---------- OAuth Callback----------
@router.get("/google/callback")
async def google_callback(
    request: Request,
    conn=Depends(get_db)
):
    
    print("SESSION:", request.session)
    print("STATE:", request.query_params.get("state"))

    token = await oauth.google.authorize_access_token(request)

    print("GOOGLE TOKEN:")
    print(token)

    google_user = token["userinfo"]

    print("GOOGLE USER:")
    print(google_user)

    if not google_user:
        raise HTTPException(
            status_code=400,
            detail="Could not get Google user information"
        )

    user = oauth_service.get_or_create_google_user(
        google_user,
        conn
    )

    print("LOCAL USER:")
    print(user)

    # create/find user here

    access_token = create_access_token(
        {
            "sub": str(user["user_id"])
        }
    )

    refresh_token = create_refresh_token(
        {
            "sub": str(user["user_id"])
        }
    )

    return RedirectResponse(
    url=
    f"{FRONTEND_URL}/oauth_success.html"
    f"?access={access_token}"
    f"&refresh={refresh_token}"
    )