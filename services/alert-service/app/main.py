import asyncio
import json
import structlog
from confluent_kafka import Consumer, KafkaError
from app.config import get_settings
from app.database import engine, Base, AsyncSessionLocal
from app.models import Alert
from app.rules import evaluate_sensor_reading, evaluate_truck_telemetry
from app.kafka_publisher import publish

settings = get_settings()
log      = structlog.get_logger()


async def create_alerts(alert_dicts: list[dict]) -> None:
    if not alert_dicts:
        return
    async with AsyncSessionLocal() as session:
        for data in alert_dicts:
            alert = Alert(**data)
            session.add(alert)
            log.warning('alert.created',
                        type=data['type'],
                        severity=data['severity'],
                        message=data['message'])
            publish('alert.created', str(alert.id), {
                'alert_id': str(alert.id),
                'type':     data['type'],
                'severity': data['severity'],
                'message':  data['message'],
                'metadata': data.get('alert_metadata', {}),
            })
        await session.commit()


async def process_message(topic: str, value: dict) -> None:
    if topic == 'bin.sensor.reading':
        alerts = evaluate_sensor_reading(value)
        await create_alerts(alerts)

    elif topic == 'bin.fill.critical':
        alerts = evaluate_sensor_reading({**value, 'fill_pct': value.get('fill_pct', 95)})
        await create_alerts(alerts)

    elif topic == 'truck.telemetry':
        alerts = evaluate_truck_telemetry(value)
        await create_alerts(alerts)


async def consume_loop() -> None:
    consumer = Consumer({
        'bootstrap.servers':  settings.kafka_brokers,
        'group.id':           settings.kafka_group_id,
        'auto.offset.reset':  'latest',
        'enable.auto.commit': True,
    })

    consumer.subscribe([
        'bin.sensor.reading',
        'bin.fill.critical',
        'truck.telemetry',
    ])

    log.info('alert-service started', brokers=settings.kafka_brokers)

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
                value = json.loads(msg.value().decode('utf-8'))
                await process_message(msg.topic(), value)
            except Exception as e:
                log.error('message.processing.failed',
                          topic=msg.topic(),
                          error=str(e))
    finally:
        consumer.close()


async def main() -> None:
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info('alert.tables.ready')

    await consume_loop()


if __name__ == '__main__':
    asyncio.run(main())
