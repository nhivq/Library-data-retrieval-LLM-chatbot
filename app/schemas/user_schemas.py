from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    """Request body for username/password registration."""

    username: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    """Request body for username/password login."""

    username: str
    password: str
