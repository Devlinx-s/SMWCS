from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from dataclasses import dataclass
from app.config import get_settings

settings = get_settings()
bearer   = HTTPBearer()

PERMISSIONS: dict[str, list[str]] = {
    'super_admin':     ['*'],
    'city_admin':      ['bins:*','trucks:*','drivers:*','routes:*','alerts:*','zones:*','shifts:*'],
    'ops_manager':     ['routes:*','trucks:*','drivers:*','alerts:*','shifts:*','bins:read'],
    'dispatcher':      ['routes:read','routes:update','trucks:read','alerts:*','bins:read'],
    'maintenance_tech':['bins:read','sensors:*','trucks:read'],
    'analyst':         ['analytics:*','reports:*','bins:read','routes:read','trucks:read'],
}

def has_permission(role: str, required: str) -> bool:
    perms = PERMISSIONS.get(role, [])
    if '*' in perms: return True
    resource = required.split(':')[0]
    return required in perms or f'{resource}:*' in perms

@dataclass
class CurrentUser:
    user_id: str
    role:    str
    email:   str

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer)
) -> CurrentUser:
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience='smwcs-api',
            issuer='smwcs-auth',
        )
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f'Invalid token: {e}')
    return CurrentUser(payload['sub'], payload['role'], payload['email'])

def require_permission(permission: str):
    def dep(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not has_permission(user.role, permission):
            raise HTTPException(status_code=403, detail=f'Permission "{permission}" required')
        return user
    return dep
