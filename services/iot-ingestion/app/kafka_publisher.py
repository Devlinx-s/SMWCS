from confluent_kafka import Producer
from app.config import get_settings
import json
import structlog

settings = get_settings()
log      = structlog.get_logger()

_producer = None


def get_producer() -> Producer:
    global _producer
    if _producer is None:
        _producer = Producer({
            'bootstrap.servers': settings.kafka_brokers,
            'client.id':         settings.service_name,
        })
    return _producer


def publish(topic: str, key: str, value: dict) -> None:
    try:
        producer = get_producer()
        producer.produce(
            topic,
            key=key,
            value=json.dumps(value, default=str),
            callback=lambda err, msg: (
                log.error('kafka.delivery.failed', topic=topic, error=str(err))
                if err else None
            ),
        )
        producer.poll(0)
    except Exception as e:
        log.error('kafka.publish.failed', topic=topic, error=str(e))
