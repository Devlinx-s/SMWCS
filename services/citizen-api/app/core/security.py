import uuid
from datetime import datetime, timedelta, timezone
from jose import jwt
from passlib.context import CryptContext
from app.config import get_settings

settings = get_settings()
pwd_ctx  = CryptContext(schemes=['bcrypt'], deprecated='auto')


def hash_password(plain: str) -> str:
    return pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)


def create_access_token(citizen_id: str, email: str) -> str:
    expire  = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_min
    )
    payload = {
        'sub':   citizen_id,
        'email': email,
        'exp':   expire,
        'iat':   datetime.now(timezone.utc),
        'jti':   str(uuid.uuid4()),
        'iss':   'smwcs-citizen',
        'aud':   'smwcs-citizen-app',
        'type':  'access',
    }
    return jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        audience='smwcs-citizen-app',
        issuer='smwcs-citizen',
    )
