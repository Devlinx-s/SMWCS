from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from app.database import get_db
from app.models.fleet import Shift, ShiftStatus, Truck, TruckStatus
from app.schemas.fleet import ShiftCreate, ShiftResponse
from app.core.deps import require_permission, CurrentUser
import uuid

router = APIRouter()


@router.get('/', response_model=list[ShiftResponse])
async def list_shifts(
    db:    AsyncSession = Depends(get_db),
    _user: CurrentUser  = Depends(require_permission('shifts:read')),
):
    result = await db.execute(
        select(Shift).order_by(Shift.planned_start.desc()).limit(100)
    )
    return [ShiftResponse.model_validate(s) for s in result.scalars().all()]


@router.get('/active', response_model=list[ShiftResponse])
async def list_active_shifts(
    db:    AsyncSession = Depends(get_db),
    _user: CurrentUser  = Depends(require_permission('shifts:read')),
):
    result = await db.execute(
        select(Shift).where(Shift.status == ShiftStatus.active)
    )
    return [ShiftResponse.model_validate(s) for s in result.scalars().all()]


@router.post('/', response_model=ShiftResponse, status_code=201)
async def create_shift(
    data:  ShiftCreate,
    db:    AsyncSession = Depends(get_db),
    _user: CurrentUser  = Depends(require_permission('shifts:write')),
):
    shift = Shift(
        id=uuid.uuid4(),
        truck_id=data.truck_id,
        driver_id=data.driver_id,
        planned_start=data.planned_start,
        planned_end=data.planned_end,
        notes=data.notes,
        status=ShiftStatus.scheduled,
    )
    db.add(shift)
    await db.commit()
    await db.refresh(shift)
    return ShiftResponse.model_validate(shift)


@router.post('/{shift_id}/start', response_model=ShiftResponse)
async def start_shift(
    shift_id: str,
    db:       AsyncSession = Depends(get_db),
    _user:    CurrentUser  = Depends(require_permission('shifts:write')),
):
    result = await db.execute(select(Shift).where(Shift.id == shift_id))
    shift  = result.scalar_one_or_none()
    if not shift:
        raise HTTPException(status_code=404, detail='Shift not found')
    if shift.status != ShiftStatus.scheduled:
        raise HTTPException(status_code=400, detail=f'Shift is {shift.status}, cannot start')

    shift.status       = ShiftStatus.active
    shift.actual_start = datetime.now(timezone.utc)

    result2 = await db.execute(select(Truck).where(Truck.id == shift.truck_id))
    truck   = result2.scalar_one_or_none()
    if truck:
        truck.status = TruckStatus.on_route

    await db.commit()
    await db.refresh(shift)
    return ShiftResponse.model_validate(shift)


@router.post('/{shift_id}/end', response_model=ShiftResponse)
async def end_shift(
    shift_id: str,
    db:       AsyncSession = Depends(get_db),
    _user:    CurrentUser  = Depends(require_permission('shifts:write')),
):
    result = await db.execute(select(Shift).where(Shift.id == shift_id))
    shift  = result.scalar_one_or_none()
    if not shift:
        raise HTTPException(status_code=404, detail='Shift not found')
    if shift.status != ShiftStatus.active:
        raise HTTPException(status_code=400, detail=f'Shift is {shift.status}, cannot end')

    shift.status     = ShiftStatus.completed
    shift.actual_end = datetime.now(timezone.utc)

    result2 = await db.execute(select(Truck).where(Truck.id == shift.truck_id))
    truck   = result2.scalar_one_or_none()
    if truck:
        truck.status = TruckStatus.available

    await db.commit()
    await db.refresh(shift)
    return ShiftResponse.model_validate(shift)
