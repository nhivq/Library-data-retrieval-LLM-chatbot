from jose import jwt
from datetime import datetime, timedelta


SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"


def create_access_token(data:dict):

    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(minutes=30)

    to_encode["exp"] = expire

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )