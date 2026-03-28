from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    service_name: str = 'media-service'
    service_port: int = 8012
    minio_endpoint:   str = 'http://localhost:9000'
    minio_access_key: str = 'smwcs'
    minio_secret_key: str = 'smwcs_dev_pass'
    minio_bucket:     str = 'smwcs'
    jwt_secret:       str = 'smwcs-jwt-secret'
    jwt_algorithm:    str = 'HS256'

@lru_cache
def get_settings(): return Settings()
