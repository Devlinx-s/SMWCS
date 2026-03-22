import json
import uuid
from datetime import datetime, timezone
from confluent_kafka import Producer
from app.config import get_settings
from app.database import AsyncSessionLocal
from sqlalchemy import text
import structlog

settings  = get_settings()
log       = structlog.get_logger()
_producer = None


def get_producer() -> Producer:
    global _producer
    if _producer is None:
        _producer = Producer({'bootstrap.servers': settings.kafka_brokers})
    return _producer


async def publish_route_updated(
    truck_id:        str,
    zone_id:         str,
    stop_sensor_ids: list[str],
    bins:            list,
) -> None:
    route_id = str(uuid.uuid4())
    now      = datetime.now(timezone.utc)

    stops = []
    for order, sensor_id in enumerate(stop_sensor_ids):
        b = next((x for x in bins if x.sensor_id == sensor_id), None)
        stops.append({
            'stop_order': order + 1,
            'sensor_id':  sensor_id,
            'fill_pct':   b.fill_pct if b else None,
            'lat':        b.lat      if b else None,
            'lon':        b.lon      if b else None,
        })

    # Save route and stops to PostgreSQL
    try:
        async with AsyncSessionLocal() as session:
            # Mark old active routes for this truck as cancelled
            await session.execute(text("""
                UPDATE routes
                SET status = 'cancelled'
                WHERE truck_id = :truck_id
                  AND status IN ('pending', 'active')
            """), {'truck_id': truck_id})

            # Insert new route
            await session.execute(text("""
                INSERT INTO routes
                  (id, truck_id, zone_id, status, total_stops, stops_done, generated_at)
                VALUES
                  (:id, :truck_id, :zone_id, 'active', :total_stops, 0, :now)
            """), {
                'id':          route_id,
                'truck_id':    truck_id,
                'zone_id':     zone_id,
                'total_stops': len(stops),
                'now':         now,
            })

            # Insert stops
            for stop in stops:
                await session.execute(text("""
                    INSERT INTO route_stops
                      (id, route_id, bin_id, sensor_id, stop_order,
                       fill_pct, lat, lon, completed, rfid_scanned, created_at)
                    VALUES
                      (:id, :route_id, :bin_id, :sensor_id, :stop_order,
                       :fill_pct, :lat, :lon, false, false, :now)
                """), {
                    'id':         str(uuid.uuid4()),
                    'route_id':   route_id,
                    'bin_id':     stop['sensor_id'],
                    'sensor_id':  stop['sensor_id'],
                    'stop_order': stop['stop_order'],
                    'fill_pct':   stop['fill_pct'],
                    'lat':        stop['lat'],
                    'lon':        stop['lon'],
                    'now':        now,
                })

            await session.commit()
            log.info('route.saved_to_db', route_id=route_id, stops=len(stops))

    except Exception as e:
        log.error('route.db.save.failed', error=str(e))

    # Publish to Kafka
    payload = {
        'route_id':     route_id,
        'truck_id':     truck_id,
        'zone_id':      zone_id,
        'stops':        stops,
        'total_stops':  len(stops),
        'generated_at': now.isoformat(),
    }

    try:
        get_producer().produce(
            'route.updated',
            key=truck_id,
            value=json.dumps(payload, default=str),
        )
        get_producer().poll(0)
        log.info('route.published', truck_id=truck_id, stops=len(stops))
    except Exception as e:
        log.error('route.publish.failed', error=str(e))
