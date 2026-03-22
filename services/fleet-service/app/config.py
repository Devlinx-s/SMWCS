from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    service_name: str = 'fleet-service'
    service_port: int = 8003
    debug:        bool = True

    postgres_host:     str = 'localhost'
    postgres_port:     int = 5432
    postgres_db:       str = 'smwcs'
    postgres_user:     str = 'smwcs'
    postgres_password: str = 'smwcs_dev_pass'

    redis_url:     str = 'redis://:smwcs_dev_pass@127.0.0.1:6379'
    kafka_brokers: str = 'localhost:9092'

    influx_url:            str = 'http://localhost:8086'
    influx_token:          str = 'smwcs-dev-influx-token'
    influx_org:            str = 'smwcs'
    influx_bucket_fleet:   str = 'fleet_positions'

    jwt_secret:    str = 'smwcs-jwt-secret'
    jwt_algorithm: str = 'HS256'

    @property
    def postgres_dsn(self) -> str:
        return (
            f'postgresql+asyncpg://{self.postgres_user}:'
            f'{self.postgres_password}@{self.postgres_host}:'
            f'{self.postgres_port}/{self.postgres_db}'
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
