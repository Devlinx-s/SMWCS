from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_pg_db
from app.core.deps import get_current_citizen, CurrentCitizen
from app.database import get_collection
import structlog

log    = structlog.get_logger()
router = APIRouter()


@router.get('/truck-eta')
async def get_truck_eta(
    citizen: CurrentCitizen = Depends(get_current_citizen),
    db:      AsyncSession   = Depends(get_pg_db),
):
    col         = get_collection('citizens')
    citizen_doc = await col.find_one({'_id': citizen.citizen_id})
    zone_id     = (citizen_doc or {}).get('location', {}).get('zone_id')

    result = await db.execute(text("""
        SELECT
            t.id::text,
            t.registration,
            t.status::text,
            t.current_load_kg,
            t.capacity_kg,
            d.first_name || ' ' || d.last_name AS driver_name,
            s.planned_end
        FROM trucks t
        LEFT JOIN shifts s ON s.truck_id = t.id AND s.status = 'active'
        LEFT JOIN drivers d ON d.id = s.driver_id
        WHERE t.status = 'on_route'
        ORDER BY t.registration
        LIMIT 3
    """))
    trucks = [dict(row) for row in result.mappings().all()]

    if not trucks:
        return {
            'message':      'No trucks currently on route in your area',
            'trucks':       [],
            'estimated_eta': None,
        }

    return {
        'zone_id': zone_id,
        'trucks':  trucks,
        'estimated_eta': '30-60 minutes',
        'message': f'{len(trucks)} truck(s) active in your area',
    }
