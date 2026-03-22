from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime, timedelta, timezone
from app.database import get_pg_db
from app.core.deps import get_current_citizen, CurrentCitizen
from app.database import get_collection
import structlog

log    = structlog.get_logger()
router = APIRouter()

# Nairobi collection schedule — zone code → collection days of week
# 0=Monday, 1=Tuesday, ... 6=Sunday
ZONE_SCHEDULE = {
    'NBI-WEST-A': [0, 3],   # Westlands: Monday + Thursday
    'NBI-EAST-A': [1, 4],   # Eastlands: Tuesday + Friday
    'NBI-CBD-A':  [0, 2, 4],# CBD: Monday + Wednesday + Friday
    'NBI-SOUTH-A':[2, 5],   # South: Wednesday + Saturday
}
DEFAULT_SCHEDULE = [1, 4]   # Tuesday + Friday fallback


@router.get('/schedule')
async def get_collection_schedule(
    citizen:  CurrentCitizen  = Depends(get_current_citizen),
    db:       AsyncSession    = Depends(get_pg_db),
):
    col     = get_collection('citizens')
    citizen_doc = await col.find_one({'_id': citizen.citizen_id})
    zone_id = citizen_doc.get('location', {}).get('zone_id') if citizen_doc else None

    # Get zone code from PostgreSQL
    zone_code = None
    if zone_id:
        result = await db.execute(
            text('SELECT code, name FROM zones WHERE id = :id'),
            {'id': zone_id}
        )
        row = result.mappings().first()
        if row:
            zone_code = row['code']

    collection_days = ZONE_SCHEDULE.get(zone_code, DEFAULT_SCHEDULE)

    # Generate next 30 days of collection dates
    today     = datetime.now(timezone.utc).date()
    schedule  = []
    check_date = today

    while len(schedule) < 12:  # next 12 collection events
        if check_date.weekday() in collection_days:
            schedule.append({
                'date':      check_date.isoformat(),
                'day':       check_date.strftime('%A'),
                'zone_code': zone_code or 'Unknown',
                'time':      '07:00 - 15:00 EAT',
            })
        check_date += timedelta(days=1)
        if (check_date - today).days > 60:
            break

    return {
        'zone_code':       zone_code,
        'collection_days': [
            ['Monday','Tuesday','Wednesday','Thursday',
             'Friday','Saturday','Sunday'][d]
            for d in collection_days
        ],
        'upcoming':        schedule,
    }
