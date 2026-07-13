import logging

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from psycopg2.extras import RealDictCursor

from app.database.connection import get_db
from app.core.logging import bind_request_context
from app.core.security import decode_access_token

logger = logging.getLogger(__name__)


security = HTTPBearer()


def get_current_user(
        credentials=Depends(security),
        conn=Depends(get_db)
):
    """Resolve the authenticated user from the bearer access token."""
    
    token = credentials.credentials

    try:

        payload = decode_access_token(token)

        # JWT subject values are strings by convention; convert before querying.
        user_id = int(str(payload["sub"]))

        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:

            cursor.execute(
                """
                SELECT user_id,
                       username,
                       email,
                       COALESCE(role, 'user') AS role
                FROM users
                WHERE user_id = %s
                """,
                (user_id,)
            )

            user = cursor.fetchone()

            if not user:
                logger.warning(
                    "authentication failed",
                    extra={"event": "auth_user_not_found", "user_id": user_id},
                )
                raise HTTPException(
                    status_code=401,
                    detail="User not found"
                )

            bind_request_context(user_id=user_id)
            logger.info(
                "authenticated user resolved",
                extra={"event": "auth_user_resolved", "user_id": user_id},
            )
            return dict(user)

        finally:

            cursor.close()
    
    except HTTPException:

        raise

    except Exception as exc:
        logger.warning(
            "invalid authentication token",
            extra={"event": "auth_invalid_token", "error": str(exc)},
        )
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )


def get_current_admin_user(
        user=Depends(get_current_user)
):
    """Require the current authenticated user to have the admin role."""

    if user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    return user
