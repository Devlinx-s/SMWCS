import asyncio
import structlog
import aiomqtt
from app.config import get_settings
from app.handlers import (
    handle_sensor_telemetry,
    handle_truck_position,
    handle_sensor_alert,
)

settings = get_settings()
log      = structlog.get_logger()


async def route_message(topic: str, payload: bytes) -> None:
    parts = topic.split('/')
    # Expected: smwcs / sensors|trucks / <id> / telemetry|position|alert
    if len(parts) < 4:
        return

    entity_type = parts[1]
    entity_id   = parts[2]
    msg_type    = parts[3]

    if entity_type == 'sensors':
        if msg_type == 'telemetry':
            await handle_sensor_telemetry(entity_id, payload)
        elif msg_type == 'alert':
            await handle_sensor_alert(entity_id, payload)

    elif entity_type == 'trucks':
        if msg_type == 'position':
            await handle_truck_position(entity_id, payload)


async def main() -> None:
    log.info('iot-ingestion starting',
             mqtt_host=settings.mqtt_host,
             mqtt_port=settings.mqtt_port)

    reconnect_delay = 5

    while True:
        try:
            async with aiomqtt.Client(
                hostname=settings.mqtt_host,
                port=settings.mqtt_port,
                username=settings.mqtt_username or None,
                password=settings.mqtt_password or None,
                keepalive=60,
            ) as client:
                await client.subscribe('smwcs/sensors/+/telemetry')
                await client.subscribe('smwcs/sensors/+/alert')
                await client.subscribe('smwcs/trucks/+/position')
                await client.subscribe('smwcs/trucks/+/telemetry')
                await client.subscribe('smwcs/trucks/+/rfid')

                log.info('mqtt.subscribed',
                         topics=[
                             'smwcs/sensors/+/telemetry',
                             'smwcs/sensors/+/alert',
                             'smwcs/trucks/+/position',
                         ])

                async for message in client.messages:
                    topic   = str(message.topic)
                    payload = message.payload

                    # Handle each message concurrently
                    asyncio.create_task(route_message(topic, payload))

        except aiomqtt.MqttError as e:
            log.warning('mqtt.disconnected',
                        error=str(e),
                        reconnecting_in=reconnect_delay)
            await asyncio.sleep(reconnect_delay)
        except Exception as e:
            log.error('iot.ingestion.error', error=str(e))
            await asyncio.sleep(reconnect_delay)


if __name__ == '__main__':
    asyncio.run(main())
