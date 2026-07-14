from jose import jwt
from datetime import datetime, timedelta
from backend.app.core.config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_ACCESS_TOKEN_EXPIRE_MINUTES, JWT_REFRESH_TOKEN_EXPIRE_DAYS


def create_access_token(data:dict):
    """Create a short-lived JWT for authenticated API requests."""

    to_encode = data.copy()

    expire = (datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES))

    to_encode["exp"] = expire

    token = jwt.encode(
        to_encode,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM
    )

    return token


def create_refresh_token(data:dict):
    """Create a longer-lived refresh token used to obtain new access tokens."""

    to_encode = data.copy()

    expire = (
        datetime.utcnow() + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    )

    to_encode["exp"] = expire

    # Mark refresh tokens so an access token cannot be used at /auth/refresh.
    to_encode["type"] = "refresh"


    return jwt.encode(
        to_encode,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM
    )


def decode_access_token(token:str):
    """Decode and validate an access token."""

    payload = jwt.decode(
        token,
        JWT_SECRET_KEY,
        algorithms=[JWT_ALGORITHM]
    )

    return payload


def decode_refresh_token(token: str):
    """Decode a refresh token and verify that it has the refresh marker."""

    payload = jwt.decode(
        token,
        JWT_SECRET_KEY,
        algorithms=[JWT_ALGORITHM]
    )

    if payload.get("type") != "refresh":
        raise ValueError("Invalid refresh token")

    return payload
