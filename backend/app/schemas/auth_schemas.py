from pydantic import BaseModel


class RefreshRequest(BaseModel):
    """Request body for exchanging a refresh token for an access token."""

    refresh_token: str
