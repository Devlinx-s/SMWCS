import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from app.config import get_settings
from app.database import engine, Base
from app.models import Route, RouteStop  # import so create_all sees them
from app.routers import terminal
from app.kafka.route_consumer import route_fanout_worker

settings = get_settings()
log      = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info('driver-terminal starting')
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    task = asyncio.create_task(route_fanout_worker())
    log.info('driver-terminal ready')
    yield
    task.cancel()
    await engine.dispose()
    log.info('driver-terminal stopped')


app = FastAPI(
    title='SMWCS Driver Terminal',
    description='WebSocket server for truck driver tablets — SMWCS Kenya',
    version='1.0.0',
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(terminal.router, tags=['Terminal'])


@app.get('/health')
async def health():
    return {
        'status':           'ok',
        'service':          settings.service_name,
        'connected_trucks': terminal.manager.connected_trucks,
    }
