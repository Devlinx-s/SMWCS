from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from dataclasses import dataclass
from app.config import get_settings

settings = get_settings()
bearer   = HTTPBearer(auto_error=False)

@dataclass
class CurrentUser:
    user_id: str
    role:    str

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer)
) -> CurrentUser:
    if not credentials:
        raise HTTPException(status_code=401, detail='Token required')
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience='smwcs-api',
            issuer='smwcs-auth',
        )
    except JWTError as e:
        raise HTTPException(status_code=401, detail=str(e))
    return CurrentUser(user_id=payload['sub'], role=payload['role'])
