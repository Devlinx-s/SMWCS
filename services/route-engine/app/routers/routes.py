from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.core.deps import require_permission, CurrentUser

router = APIRouter()


@router.get('/active')
async def get_active_routes(
    db:    AsyncSession = Depends(get_db),
    _user: CurrentUser  = Depends(require_permission('routes:read')),
):
    result = await db.execute(text("""
        SELECT
            r.id, r.truck_id, r.zone_id, r.status,
            r.total_stops, r.stops_done, r.generated_at,
            ROUND((r.stops_done::float / NULLIF(r.total_stops,0) * 100)::numeric, 1) AS pct_done
        FROM routes r
        WHERE r.status IN ('pending','active')
        ORDER BY r.generated_at DESC
    """))
    return [dict(row) for row in result.mappings().all()]


@router.get('/{route_id}/stops')
async def get_route_stops(
    route_id: str,
    db:       AsyncSession = Depends(get_db),
    _user:    CurrentUser  = Depends(require_permission('routes:read')),
):
    result = await db.execute(text("""
        SELECT stop_order, bin_id, sensor_id, fill_pct,
               lat, lon, completed, completed_at, rfid_scanned
        FROM route_stops
        WHERE route_id = :route_id
        ORDER BY stop_order
    """), {'route_id': route_id})
    return [dict(row) for row in result.mappings().all()]
