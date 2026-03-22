from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    service_name: str = 'iot-ingestion'
    debug:        bool = True

    # MQTT
    mqtt_host:     str = 'localhost'
    mqtt_port:     int = 1883
    mqtt_username: str = ''
    mqtt_password: str = ''

    # InfluxDB
    influx_url:            str = 'http://localhost:8086'
    influx_token:          str = 'smwcs-dev-influx-token'
    influx_org:            str = 'smwcs'
    influx_bucket_sensors: str = 'sensor_telemetry'
    influx_bucket_fleet:   str = 'fleet_positions'

    # Kafka
    kafka_brokers: str = 'localhost:9092'


@lru_cache
def get_settings() -> Settings:
    return Settings()
