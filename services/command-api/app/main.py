import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from app.config import get_settings
from app.database import engine, Base
from app.routers import fleet, alerts, analytics, websocket
from app.services.kafka_consumer import kafka_fanout_worker

settings = get_settings()
log      = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info('command-api starting')
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Start Kafka fanout in background
    task = asyncio.create_task(kafka_fanout_worker())
    log.info('command-api ready')
    yield
    task.cancel()
    await engine.dispose()
    log.info('command-api stopped')


app = FastAPI(
    title='SMWCS Command API',
    description='Command center API for SMWCS Kenya',
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

app.include_router(fleet.router,     prefix='/api/v1/fleet',     tags=['Fleet'])
app.include_router(alerts.router,    prefix='/api/v1/alerts',    tags=['Alerts'])
app.include_router(analytics.router, prefix='/api/v1/analytics', tags=['Analytics'])
app.include_router(websocket.router, tags=['WebSocket'])


@app.get('/health')
async def health():
    return {
        'status':  'ok',
        'service': settings.service_name,
        'ws_clients': 0,
    }
