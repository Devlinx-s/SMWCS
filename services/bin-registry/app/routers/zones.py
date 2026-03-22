from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.database import get_db
from app.models.bin import Zone
from app.schemas.bin import ZoneCreate, ZoneResponse
from app.core.deps import require_permission, CurrentUser
import uuid
import json

router = APIRouter()


@router.get('/', response_model=list[ZoneResponse])
async def list_zones(
    db:    AsyncSession = Depends(get_db),
    _user: CurrentUser  = Depends(require_permission('bins:read')),
):
    result = await db.execute(select(Zone).order_by(Zone.name))
    return [ZoneResponse.model_validate(z) for z in result.scalars().all()]


@router.post('/', response_model=ZoneResponse, status_code=201)
async def create_zone(
    data:  ZoneCreate,
    db:    AsyncSession = Depends(get_db),
    _user: CurrentUser  = Depends(require_permission('zones:write')),
):
    existing = await db.execute(select(Zone).where(Zone.code == data.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f'Zone code "{data.code}" already exists')

    boundary_geojson = json.dumps(data.boundary)
    zone = Zone(
        id=uuid.uuid4(),
        name=data.name,
        code=data.code.upper(),
        district=data.district,
        population=data.population,
        boundary=f'SRID=4326;{boundary_wkt_from_geojson(data.boundary)}',
    )
    db.add(zone)
    await db.commit()
    await db.refresh(zone)
    return ZoneResponse.model_validate(zone)


@router.get('/{zone_id}', response_model=ZoneResponse)
async def get_zone(
    zone_id: str,
    db:      AsyncSession = Depends(get_db),
    _user:   CurrentUser  = Depends(require_permission('bins:read')),
):
    result = await db.execute(select(Zone).where(Zone.id == zone_id))
    zone   = result.scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=404, detail='Zone not found')
    return ZoneResponse.model_validate(zone)


def boundary_wkt_from_geojson(geojson: dict) -> str:
    coords = geojson.get('coordinates', [[]])[0]
    points = ', '.join(f'{c[0]} {c[1]}' for c in coords)
    return f'POLYGON(({points}))'
