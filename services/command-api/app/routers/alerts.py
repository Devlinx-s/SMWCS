from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime, timezone
from app.database import get_db
from app.core.deps import require_permission, CurrentUser
from typing import Optional

router = APIRouter()


@router.get('/')
async def list_alerts(
    resolved:  Optional[bool] = Query(None),
    severity:  Optional[str]  = Query(None),
    zone_id:   Optional[str]  = Query(None),
    limit:     int            = Query(50, ge=1, le=200),
    db:        AsyncSession   = Depends(get_db),
    _user:     CurrentUser    = Depends(require_permission('alerts:read')),
):
    where = ['1=1']
    params: dict = {'limit': limit}

    if resolved is not None:
        where.append('resolved = :resolved')
        params['resolved'] = resolved

    if severity:
        where.append('severity = :severity')
        params['severity'] = severity

    if zone_id:
        where.append('zone_id = :zone_id')
        params['zone_id'] = zone_id

    where_clause = ' AND '.join(where)
    result = await db.execute(text(f"""
        SELECT id, type, severity, sensor_id, truck_id, zone_id,
               message, acknowledged, resolved, created_at
        FROM alerts
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT :limit
    """), params)
    rows = result.mappings().all()
    return [dict(row) for row in rows]


@router.post('/{alert_id}/acknowledge')
async def acknowledge_alert(
    alert_id: str,
    db:       AsyncSession = Depends(get_db),
    user:     CurrentUser  = Depends(require_permission('alerts:write')),
):
    result = await db.execute(
        text('SELECT id FROM alerts WHERE id = :id'),
        {'id': alert_id}
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail='Alert not found')

    await db.execute(text("""
        UPDATE alerts
        SET acknowledged    = true,
            acknowledged_by = :user_id,
            acknowledged_at = :now
        WHERE id = :id
    """), {
        'id':      alert_id,
        'user_id': user.user_id,
        'now':     datetime.now(timezone.utc),
    })
    await db.commit()
    return {'message': 'Alert acknowledged'}


@router.post('/{alert_id}/resolve')
async def resolve_alert(
    alert_id: str,
    db:       AsyncSession = Depends(get_db),
    _user:    CurrentUser  = Depends(require_permission('alerts:write')),
):
    await db.execute(text("""
        UPDATE alerts
        SET resolved    = true,
            resolved_at = :now
        WHERE id = :id
    """), {'id': alert_id, 'now': datetime.now(timezone.utc)})
    await db.commit()
    return {'message': 'Alert resolved'}


@router.get('/stats')
async def alert_stats(
    db:    AsyncSession = Depends(get_db),
    _user: CurrentUser  = Depends(require_permission('alerts:read')),
):
    result = await db.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE NOT resolved)                        AS open,
            COUNT(*) FILTER (WHERE NOT resolved AND severity='critical') AS critical,
            COUNT(*) FILTER (WHERE NOT resolved AND severity='high')     AS high,
            COUNT(*) FILTER (WHERE NOT resolved AND severity='medium')   AS medium,
            COUNT(*) FILTER (WHERE NOT resolved AND severity='low')      AS low,
            COUNT(*) FILTER (WHERE resolved)                            AS resolved
        FROM alerts
    """))
    row = result.mappings().one()
    return dict(row)
