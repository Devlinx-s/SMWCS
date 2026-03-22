from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime, timezone
import json
import structlog

from app.database import get_db
from app.services.connection_manager import manager
from app.kafka.publisher import publish

log    = structlog.get_logger()
router = APIRouter()


async def get_current_route(truck_id: str, db: AsyncSession) -> dict | None:
    result = await db.execute(text("""
        SELECT r.id::text AS route_id, r.zone_id,
               r.total_stops, r.stops_done, r.status::text
        FROM routes r
        WHERE r.truck_id = :truck_id
          AND r.status IN ('pending'::routestatus, 'active'::routestatus)
        ORDER BY r.generated_at DESC
        LIMIT 1
    """), {'truck_id': truck_id})
    route = result.mappings().first()
    if not route:
        return None

    stops_result = await db.execute(text("""
        SELECT id::text AS stop_id, stop_order, bin_id,
               sensor_id, fill_pct, lat, lon, completed
        FROM route_stops
        WHERE route_id = :route_id
        ORDER BY stop_order
    """), {'route_id': route['route_id']})

    return {
        'route_id':    route['route_id'],
        'zone_id':     route['zone_id'],
        'total_stops': route['total_stops'],
        'stops_done':  route['stops_done'],
        'status':      route['status'],
        'stops':       [dict(s) for s in stops_result.mappings().all()],
    }


@router.websocket('/ws/terminal/{truck_id}')
async def terminal_ws(
    truck_id: str,
    ws:       WebSocket,
    db:       AsyncSession = Depends(get_db),
):
    token = ws.query_params.get('token', '')
    if not token:
        await ws.close(code=4001, reason='Token required')
        return

    await manager.connect(truck_id, ws)

    route = await get_current_route(truck_id, db)
    if route:
        await ws.send_text(json.dumps({'type': 'ROUTE_FULL', 'route': route}, default=str))
        log.info('route.full.pushed', truck_id=truck_id, stops=route['total_stops'])
    else:
        await ws.send_text(json.dumps({'type': 'ROUTE_FULL', 'route': None, 'message': 'No active route'}))

    try:
        while True:
            raw      = await ws.receive_text()
            data     = json.loads(raw)
            msg_type = data.get('type', '')

            if msg_type == 'STOP_COMPLETED':
                stop_id = data.get('stop_id', '')
                now     = datetime.now(timezone.utc)

                await db.execute(text("""
                    UPDATE route_stops
                    SET completed = true, completed_at = :now
                    WHERE id = :stop_id
                """), {'stop_id': stop_id, 'now': now})

                # Cast string literals to the enum type
                await db.execute(text("""
                    UPDATE routes
                    SET stops_done = stops_done + 1,
                        status     = CASE
                            WHEN stops_done + 1 >= total_stops
                                THEN 'completed'::routestatus
                            ELSE 'active'::routestatus
                        END
                    WHERE id = (
                        SELECT route_id FROM route_stops WHERE id = :stop_id
                    )
                """), {'stop_id': stop_id})

                await db.commit()

                publish('stop.completed', truck_id, {
                    'truck_id':  truck_id,
                    'stop_id':   stop_id,
                    'timestamp': now.isoformat(),
                })

                await ws.send_text(json.dumps({
                    'type':    'STOP_CONFIRMED',
                    'stop_id': stop_id,
                }))
                log.info('stop.completed', truck_id=truck_id, stop_id=stop_id)

            elif msg_type == 'RFID_SCAN':
                bin_id  = data.get('bin_id', '')
                stop_id = data.get('stop_id', '')
                if stop_id:
                    await db.execute(text("""
                        UPDATE route_stops SET rfid_scanned = true WHERE id = :stop_id
                    """), {'stop_id': stop_id})
                    await db.commit()

                await ws.send_text(json.dumps({
                    'type':    'RFID_CONFIRMED',
                    'bin_id':  bin_id,
                    'stop_id': stop_id,
                }))
                log.info('rfid.scan', truck_id=truck_id, bin_id=bin_id)

            elif msg_type == 'DRIVER_EMERGENCY':
                lat = data.get('lat')
                lon = data.get('lon')
                now = datetime.now(timezone.utc)
                publish('alert.driver', truck_id, {
                    'truck_id':   truck_id,
                    'alert_type': 'driver_emergency',
                    'severity':   'critical',
                    'lat':        lat,
                    'lon':        lon,
                    'timestamp':  now.isoformat(),
                    'message':    f'EMERGENCY: Driver on truck {truck_id} needs assistance',
                })
                await ws.send_text(json.dumps({
                    'type':    'EMERGENCY_RECEIVED',
                    'message': 'Emergency alert sent to command center',
                }))
                log.error('driver.emergency', truck_id=truck_id, lat=lat, lon=lon)

            elif msg_type == 'POSITION_UPDATE':
                publish('truck.position', truck_id, {
                    'truck_id':  truck_id,
                    'lat':       data.get('lat'),
                    'lon':       data.get('lon'),
                    'speed_kmh': data.get('speed_kmh', 0),
                    'heading':   data.get('heading', 0),
                    'load_kg':   data.get('load_kg', 0),
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                })

            elif msg_type == 'ping':
                await ws.send_text(json.dumps({'type': 'pong'}))

    except WebSocketDisconnect:
        manager.disconnect(truck_id)
    except Exception as e:
        log.error('terminal.error', truck_id=truck_id, error=str(e))
        manager.disconnect(truck_id)


@router.get('/api/v1/terminals/status')
async def terminal_status():
    return {
        'connected_trucks': manager.connected_trucks,
        'count':            manager.count,
    }
