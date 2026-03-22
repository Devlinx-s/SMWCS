import asyncio
import json
import structlog
from datetime import datetime, timezone
from confluent_kafka import Consumer, KafkaError
from app.config import get_settings
from app.solver.state import state_manager
from app.solver.cvrp import solve_cvrp
from app.solver.distance import build_distance_matrix
from app.kafka.publisher import publish_route_updated

settings = get_settings()
log      = structlog.get_logger()

_last_optimised: dict[str, datetime] = {}
OPTIMISE_INTERVAL = 300  # 5 minutes

# Nairobi Ruai landfill (depot)
DEPOT = (-1.3031, 36.8303)


async def should_optimise(zone_id: str, force: bool = False) -> bool:
    if force:
        return True
    last    = _last_optimised.get(zone_id)
    elapsed = (datetime.now(timezone.utc) - last).total_seconds() if last else 999
    return elapsed >= OPTIMISE_INTERVAL


async def optimise_zone(zone_id: str) -> None:
    bins   = await state_manager.get_bins_for_zone(zone_id, min_fill_pct=70.0)
    trucks = await state_manager.get_available_trucks()

    if not bins:
        log.info('route.no_eligible_bins', zone_id=zone_id)
        return

    locations = [DEPOT] + [(b.lat, b.lon) for b in bins]
    matrix    = await build_distance_matrix(locations)
    routes    = solve_cvrp(bins, trucks, matrix)

    _last_optimised[zone_id] = datetime.now(timezone.utc)

    for truck_id, stop_ids in routes.items():
        await publish_route_updated(truck_id, zone_id, stop_ids, bins)


async def consume_loop() -> None:
    consumer = Consumer({
        'bootstrap.servers':  settings.kafka_brokers,
        'group.id':           'route-engine',
        'auto.offset.reset':  'latest',
        'enable.auto.commit': True,
    })
    consumer.subscribe(['bin.sensor.reading', 'bin.fill.critical', 'truck.position'])
    log.info('route-engine.kafka.listening')
    loop = asyncio.get_event_loop()

    try:
        while True:
            msg = await loop.run_in_executor(None, consumer.poll, 1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() != KafkaError._PARTITION_EOF:
                    log.error('kafka.error', error=str(msg.error()))
                continue

            try:
                value   = json.loads(msg.value().decode('utf-8'))
                topic   = msg.topic()
                zone_id = value.get('zone_id', '')

                if topic == 'bin.sensor.reading':
                    await state_manager.update_bin(
                        value.get('sensor_id', ''), value
                    )
                    if zone_id and await should_optimise(zone_id):
                        asyncio.create_task(optimise_zone(zone_id))

                elif topic == 'bin.fill.critical':
                    await state_manager.update_bin(
                        value.get('sensor_id', ''), value
                    )
                    if zone_id:
                        log.warning('route.critical_fill_trigger', zone_id=zone_id)
                        asyncio.create_task(optimise_zone(zone_id))

                elif topic == 'truck.position':
                    await state_manager.update_truck(
                        value.get('truck_id', ''), value
                    )

            except Exception as e:
                log.error('route.message.failed', error=str(e))
    finally:
        consumer.close()
