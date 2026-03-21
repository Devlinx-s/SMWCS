from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from dataclasses import dataclass
from app.core.security import decode_access_token, has_permission

bearer = HTTPBearer()


@dataclass
class CurrentUser:
    user_id: str
    role:    str
    email:   str


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer)
) -> CurrentUser:
    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f'Invalid or expired token: {e}',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    return CurrentUser(
        user_id=payload['sub'],
        role=payload['role'],
        email=payload['email'],
    )


def require_permission(permission: str):
    def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not has_permission(user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f'Role "{user.role}" does not have permission "{permission}"',
            )
        return user
    return dependency
