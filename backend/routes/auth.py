import logging

from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    Request
)
from authlib.integrations.starlette_client import OAuth
from fastapi.responses import RedirectResponse

from backend.app.database.connection import get_db
from backend.app.schemas.auth_schemas import RefreshRequest
from backend.app.schemas.user_schemas import RegisterRequest, LoginRequest
from backend.app.services import auth_service 
from backend.app.core.dependencies import get_current_user
from backend.app.core.security import create_access_token, decode_refresh_token, create_refresh_token
from backend.app.core.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI, FRONTEND_URL
from backend.app.services import oauth_service


logger = logging.getLogger(__name__)

router=APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


# Authlib OAuth registry. Google uses OpenID Connect metadata so Authlib can
# discover authorization, token, and userinfo endpoints.
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
    """Return the user resolved from the current bearer token."""

    return user


@router.post("/refresh")
def refresh_token(
    payload: RefreshRequest
):
    """Exchange a valid refresh token for a new access token."""
    
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


@router.post("/register")
def register(
        user: RegisterRequest,
        conn=Depends(get_db)
):
    """Create a new username/password account."""

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


@router.post("/login")
def login(
        user: LoginRequest,
        conn=Depends(get_db)
):
    """Authenticate username/password credentials."""

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


@router.get("/google")
async def google_login(
    request: Request
):
    """Start the Google OAuth redirect flow."""
    
    redirect_uri = GOOGLE_REDIRECT_URI

    return await oauth.google.authorize_redirect(
        request,
        redirect_uri
    )


@router.get("/google/callback")
async def google_callback(
    request: Request,
    conn=Depends(get_db)
):
    """Handle Google's OAuth callback and redirect the frontend with tokens."""
    
    logger.info(
        "Google OAuth callback received",
        extra={
            "event": "google_oauth_callback",
            "session_id": request.session.get("state"),
            "state": request.query_params.get("state"),
        },
    )

    token = await oauth.google.authorize_access_token(request)

    google_user = token["userinfo"]

    logger.info(
        "Google user profile resolved",
        extra={"event": "google_user_profile", "user_email": google_user.get("email")},
    )

    if not google_user:
        raise HTTPException(
            status_code=400,
            detail="Could not get Google user information"
        )

    user = oauth_service.get_or_create_google_user(
        google_user,
        conn
    )

    logger.info(
        "local user account resolved",
        extra={"event": "oauth_local_user", "user_id": user.get("user_id")},
    )

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

    # The frontend success page receives the tokens after Google redirects
    # back to the backend and the backend verifies the Google profile.
    return RedirectResponse(
        url=
        f"{FRONTEND_URL}/oauth-success"
        f"?access={access_token}"
        f"&refresh={refresh_token}"
    )
