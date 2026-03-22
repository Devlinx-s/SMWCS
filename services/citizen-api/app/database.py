from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy.ext.asyncio import (
    create_async_engine, AsyncSession, async_sessionmaker
)
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings
from functools import lru_cache

settings = get_settings()

# ── MongoDB (citizen data) ────────────────────────────────────────────────────
_mongo_client: AsyncIOMotorClient | None = None


def get_mongo_client() -> AsyncIOMotorClient:
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = AsyncIOMotorClient(settings.mongo_uri)
    return _mongo_client


def get_mongo_db():
    return get_mongo_client()[settings.mongo_db]


def get_collection(name: str):
    return get_mongo_db()[name]


# ── PostgreSQL (zones/trucks read-only) ───────────────────────────────────────
engine = create_async_engine(
    settings.postgres_dsn,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_pg_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
