from pydantic import BaseModel

# ---------- Request Models ----------
class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str