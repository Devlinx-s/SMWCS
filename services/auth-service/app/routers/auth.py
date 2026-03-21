from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as aioredis
from datetime import datetime, timezone, timedelta
import structlog

from app.database import get_db
from app.models.user import SystemUser
from app.schemas.auth import (
    LoginRequest, LoginResponse, RefreshRequest, TokenResponse,
    MFASetupResponse, MFAVerifyRequest, ChangePasswordRequest, UserResponse,
)
from app.core.security import (
    verify_password, create_access_token, create_refresh_token,
    generate_mfa_secret, get_provisioning_uri, generate_qr_code_b64,
    verify_totp, hash_password,
)
from app.core.deps import get_current_user, CurrentUser
from app.config import get_settings

settings = get_settings()
log      = structlog.get_logger()
router   = APIRouter()


async def get_redis():
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        yield r
    finally:
        await r.aclose()


@router.post('/login', response_model=LoginResponse)
async def login(
    data: LoginRequest,
    db:   AsyncSession = Depends(get_db),
    r:    aioredis.Redis = Depends(get_redis),
):
    result = await db.execute(select(SystemUser).where(SystemUser.email == data.email))
    user   = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Incorrect email or password')

    if not user.is_active:
        raise HTTPException(status_code=403, detail='Account is deactivated')

    if user.mfa_enabled:
        if not data.totp_code:
            raise HTTPException(status_code=403, detail='MFA code required')
        if not verify_totp(user.mfa_secret, data.totp_code):
            raise HTTPException(status_code=401, detail='Invalid MFA code')

    access_token  = create_access_token(str(user.id), user.role.value, user.email)
    refresh_token = create_refresh_token()

    await r.setex(
        f'refresh:{refresh_token}',
        int(timedelta(days=settings.refresh_token_expire_days).total_seconds()),
        str(user.id),
    )

    user.last_login = datetime.now(timezone.utc)
    await db.commit()
    log.info('user.login', user_id=str(user.id), email=user.email)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post('/refresh', response_model=TokenResponse)
async def refresh(
    data: RefreshRequest,
    db:   AsyncSession = Depends(get_db),
    r:    aioredis.Redis = Depends(get_redis),
):
    user_id = await r.get(f'refresh:{data.refresh_token}')
    if not user_id:
        raise HTTPException(status_code=401, detail='Invalid or expired refresh token')

    result = await db.execute(select(SystemUser).where(SystemUser.id == user_id))
    user   = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail='User not found or inactive')

    return TokenResponse(access_token=create_access_token(str(user.id), user.role.value, user.email))


@router.post('/logout')
async def logout(data: RefreshRequest, r: aioredis.Redis = Depends(get_redis)):
    await r.delete(f'refresh:{data.refresh_token}')
    return {'message': 'Logged out successfully'}


@router.get('/me', response_model=UserResponse)
async def get_me(
    user: CurrentUser = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    result  = await db.execute(select(SystemUser).where(SystemUser.id == user.user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail='User not found')
    return UserResponse.model_validate(db_user)


@router.post('/mfa/setup', response_model=MFASetupResponse)
async def setup_mfa(
    user: CurrentUser = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    result  = await db.execute(select(SystemUser).where(SystemUser.id == user.user_id))
    db_user = result.scalar_one_or_none()
    secret  = generate_mfa_secret()
    db_user.mfa_secret = secret
    await db.commit()
    return MFASetupResponse(secret=secret, qr_code=generate_qr_code_b64(get_provisioning_uri(secret, db_user.email)))


@router.post('/mfa/verify')
async def verify_mfa(
    data: MFAVerifyRequest,
    user: CurrentUser = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    result  = await db.execute(select(SystemUser).where(SystemUser.id == user.user_id))
    db_user = result.scalar_one_or_none()
    if not db_user or not db_user.mfa_secret:
        raise HTTPException(status_code=400, detail='MFA setup not started')
    if not verify_totp(db_user.mfa_secret, data.totp_code):
        raise HTTPException(status_code=400, detail='Invalid TOTP code')
    db_user.mfa_enabled = True
    await db.commit()
    return {'message': 'MFA enabled successfully'}


@router.post('/change-password')
async def change_password(
    data: ChangePasswordRequest,
    user: CurrentUser = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    result  = await db.execute(select(SystemUser).where(SystemUser.id == user.user_id))
    db_user = result.scalar_one_or_none()
    if not verify_password(data.current_password, db_user.password_hash):
        raise HTTPException(status_code=400, detail='Current password is incorrect')
    db_user.password_hash = hash_password(data.new_password)
    await db.commit()
    return {'message': 'Password changed successfully'}
