import asyncio
import json
import structlog
from pydantic import ValidationError
from app.schemas import SensorTelemetry, TruckPosition, SensorAlert
from app.influx_writer import write_sensor_reading, write_truck_position
from app.kafka_publisher import publish

log = structlog.get_logger()

# Fill thresholds
FILL_ALERT_PCT    = 80
FILL_CRITICAL_PCT = 90


async def handle_sensor_telemetry(sensor_id: str, raw: bytes) -> None:
    try:
        data = json.loads(raw)
        if 'sensor_id' not in data:
            data['sensor_id'] = sensor_id
        if 'timestamp' not in data:
            from datetime import datetime, timezone
            data['timestamp'] = datetime.now(timezone.utc).isoformat()

        payload = SensorTelemetry.model_validate(data)
    except (ValidationError, json.JSONDecodeError) as e:
        log.warning('sensor.payload.invalid',
                    sensor_id=sensor_id, error=str(e))
        return

    # Write to InfluxDB
    await write_sensor_reading(payload.model_dump(mode='json'))

    # Publish to Kafka
    publish('bin.sensor.reading', sensor_id, payload.model_dump(mode='json'))

    # Critical fill alert
    if payload.fill_pct >= FILL_CRITICAL_PCT:
        publish('bin.fill.critical', sensor_id, {
            'sensor_id': sensor_id,
            'fill_pct':  payload.fill_pct,
            'zone_id':   payload.zone_id,
            'timestamp': payload.timestamp.isoformat(),
        })
        log.warning('bin.fill.critical',
                    sensor_id=sensor_id,
                    fill_pct=payload.fill_pct)

    elif payload.fill_pct >= FILL_ALERT_PCT:
        log.info('bin.fill.high',
                 sensor_id=sensor_id,
                 fill_pct=payload.fill_pct)

    # Fire alert
    if payload.temp_c >= 60:
        publish('bin.alert', sensor_id, {
            'sensor_id':  sensor_id,
            'alert_type': 'bin_fire',
            'severity':   'critical',
            'temp_c':     payload.temp_c,
            'timestamp':  payload.timestamp.isoformat(),
        })
        log.error('bin.fire.alert',
                  sensor_id=sensor_id,
                  temp_c=payload.temp_c)


async def handle_truck_position(truck_id: str, raw: bytes) -> None:
    try:
        data = json.loads(raw)
        if 'truck_id' not in data:
            data['truck_id'] = truck_id
        if 'timestamp' not in data:
            from datetime import datetime, timezone
            data['timestamp'] = datetime.now(timezone.utc).isoformat()

        payload = TruckPosition.model_validate(data)
    except (ValidationError, json.JSONDecodeError) as e:
        log.warning('truck.payload.invalid',
                    truck_id=truck_id, error=str(e))
        return

    await write_truck_position(payload.model_dump(mode='json'))
    publish('truck.position', truck_id, payload.model_dump(mode='json'))


async def handle_sensor_alert(sensor_id: str, raw: bytes) -> None:
    try:
        data    = json.loads(raw)
        if 'sensor_id' not in data:
            data['sensor_id'] = sensor_id
        if 'timestamp' not in data:
            from datetime import datetime, timezone
            data['timestamp'] = datetime.now(timezone.utc).isoformat()

        payload = SensorAlert.model_validate(data)
    except (ValidationError, json.JSONDecodeError) as e:
        log.warning('sensor.alert.invalid', error=str(e))
        return

    publish('bin.alert', sensor_id, payload.model_dump(mode='json'))
    log.warning('sensor.alert.received',
                sensor_id=sensor_id,
                alert_type=payload.alert_type,
                severity=payload.severity)
