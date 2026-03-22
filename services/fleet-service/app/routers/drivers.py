from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.fleet import Driver, DriverStatus
from app.schemas.fleet import DriverCreate, DriverUpdate, DriverResponse
from app.core.deps import require_permission, CurrentUser
from typing import Optional
import uuid

router = APIRouter()


@router.get('/', response_model=list[DriverResponse])
async def list_drivers(
    status: Optional[str] = Query(None),
    db:     AsyncSession   = Depends(get_db),
    _user:  CurrentUser    = Depends(require_permission('drivers:read')),
):
    q = select(Driver)
    if status:
        q = q.where(Driver.status == status)
    q = q.order_by(Driver.last_name)
    result = await db.execute(q)
    return [DriverResponse.model_validate(d) for d in result.scalars().all()]


@router.post('/', response_model=DriverResponse, status_code=201)
async def create_driver(
    data:  DriverCreate,
    db:    AsyncSession = Depends(get_db),
    _user: CurrentUser  = Depends(require_permission('drivers:write')),
):
    existing = await db.execute(
        select(Driver).where(Driver.employee_id == data.employee_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail='Employee ID already registered')

    driver = Driver(
        id=uuid.uuid4(),
        employee_id=data.employee_id,
        first_name=data.first_name,
        last_name=data.last_name,
        phone=data.phone,
        email=data.email,
        license_number=data.license_number,
        license_expiry=data.license_expiry,
        status=DriverStatus.active,
    )
    db.add(driver)
    await db.commit()
    await db.refresh(driver)
    return DriverResponse.model_validate(driver)


@router.get('/{driver_id}', response_model=DriverResponse)
async def get_driver(
    driver_id: str,
    db:        AsyncSession = Depends(get_db),
    _user:     CurrentUser  = Depends(require_permission('drivers:read')),
):
    result = await db.execute(select(Driver).where(Driver.id == driver_id))
    driver = result.scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=404, detail='Driver not found')
    return DriverResponse.model_validate(driver)


@router.patch('/{driver_id}', response_model=DriverResponse)
async def update_driver(
    driver_id: str,
    data:      DriverUpdate,
    db:        AsyncSession = Depends(get_db),
    _user:     CurrentUser  = Depends(require_permission('drivers:write')),
):
    result = await db.execute(select(Driver).where(Driver.id == driver_id))
    driver = result.scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=404, detail='Driver not found')
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(driver, field, value)
    await db.commit()
    await db.refresh(driver)
    return DriverResponse.model_validate(driver)
