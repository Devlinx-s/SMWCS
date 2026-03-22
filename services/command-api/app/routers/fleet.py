from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.database import get_db
from app.core.deps import require_permission, CurrentUser
import structlog

log    = structlog.get_logger()
router = APIRouter()


@router.get('/live')
async def get_live_fleet(
    db:    AsyncSession = Depends(get_db),
    _user: CurrentUser  = Depends(require_permission('trucks:read')),
):
    result = await db.execute(text("""
        SELECT
            t.id,
            t.registration,
            t.make,
            t.model,
            t.status,
            t.current_load_kg,
            t.capacity_kg,
            t.fuel_type,
            t.gps_unit_id,
            ROUND((t.current_load_kg::float / NULLIF(t.capacity_kg, 0) * 100)::numeric, 1) AS load_pct,
            d.first_name || ' ' || d.last_name AS driver_name,
            d.phone AS driver_phone,
            s.id AS shift_id,
            s.planned_start,
            s.planned_end
        FROM trucks t
        LEFT JOIN shifts s ON s.truck_id = t.id AND s.status = 'active'
        LEFT JOIN drivers d ON d.id = s.driver_id
        ORDER BY t.registration
    """))
    rows = result.mappings().all()
    return [dict(row) for row in rows]


@router.get('/stats')
async def get_fleet_stats(
    db:    AsyncSession = Depends(get_db),
    _user: CurrentUser  = Depends(require_permission('trucks:read')),
):
    result = await db.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE status = 'available')   AS available,
            COUNT(*) FILTER (WHERE status = 'on_route')    AS on_route,
            COUNT(*) FILTER (WHERE status = 'maintenance') AS maintenance,
            COUNT(*) FILTER (WHERE status = 'offline')     AS offline,
            COUNT(*) AS total
        FROM trucks
    """))
    row = result.mappings().one()
    return dict(row)
