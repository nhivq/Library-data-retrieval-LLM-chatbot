from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

from app.core.security import decode_access_token


security = HTTPBearer()


def get_current_user(
        credentials=Depends(security)
):
    
    token = credentials.credentials

    try:

        payload = decode_access_token(token)

        user_id = int(str(payload["sub"]))

        return {"user_id": user_id}
    
    except Exception:

        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )
