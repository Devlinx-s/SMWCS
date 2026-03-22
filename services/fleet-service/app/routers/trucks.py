from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.fleet import Truck, TruckStatus
from app.schemas.fleet import TruckCreate, TruckUpdate, TruckResponse
from app.core.deps import require_permission, CurrentUser
from typing import Optional
import uuid

router = APIRouter()


@router.get('/', response_model=list[TruckResponse])
async def list_trucks(
    status:  Optional[str] = Query(None),
    db:      AsyncSession  = Depends(get_db),
    _user:   CurrentUser   = Depends(require_permission('trucks:read')),
):
    q = select(Truck)
    if status:
        q = q.where(Truck.status == status)
    q = q.order_by(Truck.registration)
    result = await db.execute(q)
    return [TruckResponse.model_validate(t) for t in result.scalars().all()]


@router.post('/', response_model=TruckResponse, status_code=201)
async def create_truck(
    data:  TruckCreate,
    db:    AsyncSession = Depends(get_db),
    _user: CurrentUser  = Depends(require_permission('trucks:write')),
):
    existing = await db.execute(
        select(Truck).where(Truck.registration == data.registration)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail='Registration already exists')

    truck = Truck(
        id=uuid.uuid4(),
        registration=data.registration.upper(),
        make=data.make,
        model=data.model,
        year=data.year,
        capacity_kg=data.capacity_kg,
        capacity_litres=data.capacity_litres,
        fuel_type=data.fuel_type,
        gps_unit_id=data.gps_unit_id,
        status=TruckStatus.available,
    )
    db.add(truck)
    await db.commit()
    await db.refresh(truck)
    return TruckResponse.model_validate(truck)


@router.get('/{truck_id}', response_model=TruckResponse)
async def get_truck(
    truck_id: str,
    db:       AsyncSession = Depends(get_db),
    _user:    CurrentUser  = Depends(require_permission('trucks:read')),
):
    result = await db.execute(select(Truck).where(Truck.id == truck_id))
    truck  = result.scalar_one_or_none()
    if not truck:
        raise HTTPException(status_code=404, detail='Truck not found')
    return TruckResponse.model_validate(truck)


@router.patch('/{truck_id}', response_model=TruckResponse)
async def update_truck(
    truck_id: str,
    data:     TruckUpdate,
    db:       AsyncSession = Depends(get_db),
    _user:    CurrentUser  = Depends(require_permission('trucks:write')),
):
    result = await db.execute(select(Truck).where(Truck.id == truck_id))
    truck  = result.scalar_one_or_none()
    if not truck:
        raise HTTPException(status_code=404, detail='Truck not found')
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(truck, field, value)
    await db.commit()
    await db.refresh(truck)
    return TruckResponse.model_validate(truck)


@router.delete('/{truck_id}', status_code=204)
async def decommission_truck(
    truck_id: str,
    db:       AsyncSession = Depends(get_db),
    _user:    CurrentUser  = Depends(require_permission('trucks:write')),
):
    result = await db.execute(select(Truck).where(Truck.id == truck_id))
    truck  = result.scalar_one_or_none()
    if not truck:
        raise HTTPException(status_code=404, detail='Truck not found')
    truck.status = TruckStatus.offline
    await db.commit()
