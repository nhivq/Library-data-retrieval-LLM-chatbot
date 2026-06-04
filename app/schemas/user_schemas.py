from pydantic import BaseModel, EmailStr

# ---------- Request Models ----------
class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str