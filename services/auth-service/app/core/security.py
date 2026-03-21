import uuid
from datetime import datetime, timedelta, timezone
from jose import jwt
from passlib.context import CryptContext
import pyotp
import qrcode
import io
import base64
from app.config import get_settings

settings = get_settings()
pwd_ctx  = CryptContext(schemes=['bcrypt'], deprecated='auto')


def hash_password(plain: str) -> str:
    return pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)


def create_access_token(user_id: str, role: str, email: str) -> str:
    expire  = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_min)
    payload = {
        'sub':   user_id,
        'role':  role,
        'email': email,
        'exp':   expire,
        'iat':   datetime.now(timezone.utc),
        'jti':   str(uuid.uuid4()),
        'iss':   'smwcs-auth',
        'aud':   'smwcs-api',
        'type':  'access',
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token() -> str:
    return str(uuid.uuid4())


def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        audience='smwcs-api',
        issuer='smwcs-auth',
    )


PERMISSIONS: dict[str, list[str]] = {
    'super_admin':     ['*'],
    'city_admin':      ['bins:*', 'trucks:*', 'drivers:*', 'routes:*', 'alerts:*', 'users:read', 'zones:*', 'shifts:*'],
    'ops_manager':     ['routes:*', 'trucks:*', 'drivers:*', 'alerts:*', 'shifts:*', 'bins:read'],
    'dispatcher':      ['routes:read', 'routes:update', 'trucks:read', 'alerts:*', 'bins:read'],
    'maintenance_tech':['bins:read', 'sensors:*', 'trucks:read'],
    'analyst':         ['analytics:*', 'reports:*', 'bins:read', 'routes:read', 'trucks:read'],
}


def has_permission(role: str, required: str) -> bool:
    perms = PERMISSIONS.get(role, [])
    if '*' in perms:
        return True
    resource = required.split(':')[0]
    return required in perms or f'{resource}:*' in perms


def generate_mfa_secret() -> str:
    return pyotp.random_base32()


def get_provisioning_uri(secret: str, email: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name='SMWCS Kenya')


def generate_qr_code_b64(otpauth_uri: str) -> str:
    img = qrcode.make(otpauth_uri)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode()


def verify_totp(secret: str, token: str) -> bool:
    return pyotp.TOTP(secret).verify(token, valid_window=1)
