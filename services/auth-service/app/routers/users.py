from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import SystemUser
from app.schemas.auth import UserCreate, UserResponse
from app.core.security import hash_password
from app.core.deps import require_permission, CurrentUser

router = APIRouter()


@router.get('/', response_model=list[UserResponse])
async def list_users(
    db:    AsyncSession = Depends(get_db),
    _user: CurrentUser  = Depends(require_permission('users:read')),
):
    result = await db.execute(select(SystemUser).order_by(SystemUser.created_at.desc()))
    return [UserResponse.model_validate(u) for u in result.scalars().all()]


@router.post('/', response_model=UserResponse, status_code=201)
async def create_user(
    data:  UserCreate,
    db:    AsyncSession = Depends(get_db),
    _user: CurrentUser  = Depends(require_permission('users:read')),
):
    existing = await db.execute(select(SystemUser).where(SystemUser.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail='Email already registered')

    user = SystemUser(
        email=data.email,
        password_hash=hash_password(data.password),
        first_name=data.first_name,
        last_name=data.last_name,
        role=data.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.patch('/{user_id}/deactivate')
async def deactivate_user(
    user_id: str,
    db:      AsyncSession = Depends(get_db),
    _user:   CurrentUser  = Depends(require_permission('users:read')),
):
    result  = await db.execute(select(SystemUser).where(SystemUser.id == user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail='User not found')
    db_user.is_active = False
    await db.commit()
    return {'message': f'User {db_user.email} deactivated'}
