import asyncio
import json
import structlog
from confluent_kafka import Consumer, KafkaError
from app.config import get_settings
from app.services.connection_manager import manager

settings = get_settings()
log      = structlog.get_logger()


async def route_fanout_worker() -> None:
    """
    Consumes route.updated and alert.driver from Kafka.
    Pushes ROUTE_DELTA and DRIVER_ALERT to the relevant truck's WebSocket.
    """
    consumer = Consumer({
        'bootstrap.servers':  settings.kafka_brokers,
        'group.id':           'driver-terminal-fanout',
        'auto.offset.reset':  'latest',
        'enable.auto.commit': True,
    })
    consumer.subscribe(['route.updated', 'alert.driver'])
    log.info('driver-terminal.kafka.listening')
    loop = asyncio.get_event_loop()

    try:
        while True:
            msg = await loop.run_in_executor(None, consumer.poll, 0.5)

            if msg is None:
                continue
            if msg.error():
                if msg.error().code() != KafkaError._PARTITION_EOF:
                    log.error('kafka.error', error=str(msg.error()))
                continue

            try:
                value    = json.loads(msg.value().decode('utf-8'))
                truck_id = value.get('truck_id', '')
                topic    = msg.topic()

                if topic == 'route.updated':
                    sent = await manager.send(truck_id, {
                        'type':  'ROUTE_DELTA',
                        'route': value,
                    })
                    if sent:
                        log.info('route.delta.pushed',
                                 truck_id=truck_id,
                                 stops=value.get('total_stops', 0))
                    else:
                        log.info('route.delta.no_terminal',
                                 truck_id=truck_id)

                elif topic == 'alert.driver':
                    sent = await manager.send(truck_id, {
                        'type':  'DRIVER_ALERT',
                        'alert': value,
                    })
                    log.warning('driver.alert.pushed',
                                truck_id=truck_id,
                                sent=sent)

            except Exception as e:
                log.error('fanout.message.failed', error=str(e))
    finally:
        consumer.close()
