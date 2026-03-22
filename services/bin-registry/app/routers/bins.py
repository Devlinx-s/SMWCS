from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from geoalchemy2.functions import ST_SetSRID, ST_MakePoint
from app.database import get_db
from app.models.bin import Bin, BinStatus
from app.schemas.bin import BinCreate, BinUpdate, BinResponse, BinFillSummary
from app.core.deps import require_permission, CurrentUser
import uuid
from typing import Optional

router = APIRouter()


@router.get('/', response_model=list[BinResponse])
async def list_bins(
    zone_id:      Optional[str]   = Query(None),
    status:       Optional[str]   = Query(None),
    page:         int             = Query(1, ge=1),
    per_page:     int             = Query(50, ge=1, le=200),
    db:           AsyncSession    = Depends(get_db),
    _user:        CurrentUser     = Depends(require_permission('bins:read')),
):
    q = select(Bin)
    if zone_id:
        q = q.where(Bin.zone_id == zone_id)
    if status:
        q = q.where(Bin.status == status)
    q = q.order_by(Bin.created_at.desc())
    q = q.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(q)
    return [BinResponse.model_validate(b) for b in result.scalars().all()]


@router.post('/', response_model=BinResponse, status_code=201)
async def create_bin(
    data:  BinCreate,
    db:    AsyncSession = Depends(get_db),
    _user: CurrentUser  = Depends(require_permission('bins:write')),
):
    existing = await db.execute(select(Bin).where(Bin.serial_number == data.serial_number))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail='Serial number already registered')

    bin_obj = Bin(
        id=uuid.uuid4(),
        serial_number=data.serial_number,
        location=ST_SetSRID(ST_MakePoint(data.location.lon, data.location.lat), 4326),
        zone_id=data.zone_id,
        sensor_id=data.sensor_id,
        address=data.address,
        capacity_litres=data.capacity_litres,
        status=BinStatus.active,
    )
    db.add(bin_obj)
    await db.commit()
    await db.refresh(bin_obj)
    return BinResponse.model_validate(bin_obj)


@router.get('/zone/{zone_id}/summary', response_model=BinFillSummary)
async def zone_fill_summary(
    zone_id: str,
    db:      AsyncSession = Depends(get_db),
    _user:   CurrentUser  = Depends(require_permission('bins:read')),
):
    result = await db.execute(
        select(func.count(Bin.id)).where(Bin.zone_id == zone_id)
    )
    total = result.scalar() or 0
    return BinFillSummary(
        zone_id=zone_id,
        total=total,
        below_50=0,
        between_50_80=0,
        above_80=0,
        critical=0,
    )


@router.get('/{bin_id}', response_model=BinResponse)
async def get_bin(
    bin_id: str,
    db:     AsyncSession = Depends(get_db),
    _user:  CurrentUser  = Depends(require_permission('bins:read')),
):
    result  = await db.execute(select(Bin).where(Bin.id == bin_id))
    bin_obj = result.scalar_one_or_none()
    if not bin_obj:
        raise HTTPException(status_code=404, detail='Bin not found')
    return BinResponse.model_validate(bin_obj)


@router.patch('/{bin_id}', response_model=BinResponse)
async def update_bin(
    bin_id: str,
    data:   BinUpdate,
    db:     AsyncSession = Depends(get_db),
    _user:  CurrentUser  = Depends(require_permission('bins:write')),
):
    result  = await db.execute(select(Bin).where(Bin.id == bin_id))
    bin_obj = result.scalar_one_or_none()
    if not bin_obj:
        raise HTTPException(status_code=404, detail='Bin not found')
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(bin_obj, field, value)
    await db.commit()
    await db.refresh(bin_obj)
    return BinResponse.model_validate(bin_obj)


@router.delete('/{bin_id}', status_code=204)
async def delete_bin(
    bin_id: str,
    db:     AsyncSession = Depends(get_db),
    _user:  CurrentUser  = Depends(require_permission('bins:write')),
):
    result  = await db.execute(select(Bin).where(Bin.id == bin_id))
    bin_obj = result.scalar_one_or_none()
    if not bin_obj:
        raise HTTPException(status_code=404, detail='Bin not found')
    bin_obj.status = BinStatus.decommissioned
    await db.commit()
