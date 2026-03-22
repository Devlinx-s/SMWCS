from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
from influxdb_client import Point
from datetime import timezone
import structlog
from app.config import get_settings

settings = get_settings()
log      = structlog.get_logger()


async def write_sensor_reading(payload: dict) -> None:
    try:
        async with InfluxDBClientAsync(
            url=settings.influx_url,
            token=settings.influx_token,
            org=settings.influx_org,
        ) as client:
            write_api = client.write_api()
            point = (
                Point('bin_reading')
                .tag('sensor_id',  payload['sensor_id'])
                .tag('zone_id',    payload.get('zone_id', 'unknown'))
                .tag('waste_type', payload.get('waste_type', 'unknown'))
                .field('fill_pct',    float(payload['fill_pct']))
                .field('weight_kg',   float(payload.get('weight_kg', 0)))
                .field('temp_c',      float(payload.get('temp_c', 25)))
                .field('battery_pct', int(payload.get('battery_pct', 100)))
                .field('rssi',        int(payload.get('rssi', -70)))
            )
            await write_api.write(
                bucket=settings.influx_bucket_sensors,
                record=point,
            )
            log.info('sensor.written',
                     sensor_id=payload['sensor_id'],
                     fill_pct=payload['fill_pct'])
    except Exception as e:
        log.error('influx.write.failed', error=str(e), sensor_id=payload.get('sensor_id'))


async def write_truck_position(payload: dict) -> None:
    try:
        async with InfluxDBClientAsync(
            url=settings.influx_url,
            token=settings.influx_token,
            org=settings.influx_org,
        ) as client:
            write_api = client.write_api()
            point = (
                Point('truck_position')
                .tag('truck_id', payload['truck_id'])
                .field('lat',       float(payload['lat']))
                .field('lon',       float(payload['lon']))
                .field('speed_kmh', float(payload.get('speed_kmh', 0)))
                .field('heading',   float(payload.get('heading', 0)))
                .field('load_kg',   int(payload.get('load_kg', 0)))
                .field('fuel_pct',  float(payload.get('fuel_pct', 100)))
            )
            await write_api.write(
                bucket=settings.influx_bucket_fleet,
                record=point,
            )
    except Exception as e:
        log.error('influx.truck.write.failed', error=str(e), truck_id=payload.get('truck_id'))
