from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.core.deps import require_permission, CurrentUser

router = APIRouter()


@router.get('/summary')
async def get_summary(
    db:    AsyncSession = Depends(get_db),
    _user: CurrentUser  = Depends(require_permission('analytics:read')),
):
    trucks = await db.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE status = 'on_route') AS trucks_active,
            COUNT(*) AS trucks_total
        FROM trucks
    """))
    t = dict(trucks.mappings().one())

    bins = await db.execute(text("""
        SELECT
            COUNT(*) AS bins_total,
            COUNT(*) FILTER (WHERE status = 'active') AS bins_active
        FROM bins
    """))
    b = dict(bins.mappings().one())

    alerts = await db.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE NOT resolved) AS open_alerts,
            COUNT(*) FILTER (WHERE NOT resolved AND severity = 'critical') AS critical_alerts
        FROM alerts
    """))
    a = dict(alerts.mappings().one())

    drivers = await db.execute(text("""
        SELECT COUNT(*) AS drivers_active
        FROM drivers WHERE status = 'active'
    """))
    d = dict(drivers.mappings().one())

    return {
        'trucks':  t,
        'bins':    b,
        'alerts':  a,
        'drivers': d,
    }
