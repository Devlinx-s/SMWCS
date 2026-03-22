from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    service_name: str = 'citizen-api'
    service_port: int = 8008
    debug:        bool = True

    mongo_uri: str = 'mongodb://localhost:27018'
    mongo_db:  str = 'smwcs_citizen'

    postgres_host:     str = 'localhost'
    postgres_port:     int = 5432
    postgres_db:       str = 'smwcs'
    postgres_user:     str = 'smwcs'
    postgres_password: str = 'smwcs_dev_pass'

    kafka_brokers: str = 'localhost:9092'

    jwt_secret:                str = 'smwcs-citizen-jwt-secret'
    jwt_algorithm:             str = 'HS256'
    access_token_expire_min:   int = 60
    refresh_token_expire_days: int = 30

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
