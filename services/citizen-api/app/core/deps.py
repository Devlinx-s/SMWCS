from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from dataclasses import dataclass
from app.core.security import decode_token

bearer = HTTPBearer()


@dataclass
class CurrentCitizen:
    citizen_id: str
    email:      str


def get_current_citizen(
    credentials: HTTPAuthorizationCredentials = Depends(bearer)
) -> CurrentCitizen:
    try:
        payload = decode_token(credentials.credentials)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f'Invalid token: {e}',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    return CurrentCitizen(
        citizen_id=payload['sub'],
        email=payload['email'],
    )
