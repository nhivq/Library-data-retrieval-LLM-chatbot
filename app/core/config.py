import os
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET_KEY="change-this-later"
JWT_ALGORITHM="HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS = 30

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI",
    "http://127.0.0.1:8000/auth/google/callback"
)
FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://127.0.0.1:5500/frontend"
)
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY")