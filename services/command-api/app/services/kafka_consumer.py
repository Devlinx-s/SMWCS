import asyncio
import json
import structlog
from confluent_kafka import Consumer, KafkaError
from app.config import get_settings
from app.services.broadcaster import broadcaster

settings = get_settings()
log      = structlog.get_logger()


async def kafka_fanout_worker() -> None:
    consumer = Consumer({
        'bootstrap.servers':  settings.kafka_brokers,
        'group.id':           'command-api-fanout',
        'auto.offset.reset':  'latest',
        'enable.auto.commit': True,
    })

    consumer.subscribe([
        'truck.position',
        'alert.created',
        'bin.fill.critical',
        'bin.sensor.reading',
        'route.updated',
    ])

    log.info('kafka.fanout.started')
    loop = asyncio.get_event_loop()

    try:
        while True:
            msg = await loop.run_in_executor(None, consumer.poll, 0.5)

            if msg is None:
                continue
            if msg.error():
                if msg.error().code() != KafkaError._PARTITION_EOF:
                    log.error('kafka.fanout.error', error=str(msg.error()))
                continue

            try:
                value     = json.loads(msg.value().decode('utf-8'))
                msg_type  = msg.topic().upper().replace('.', '_')
                await broadcaster.broadcast({
                    'type': msg_type,
                    'data': value,
                })
            except Exception as e:
                log.error('fanout.failed', error=str(e))
    finally:
        consumer.close()
