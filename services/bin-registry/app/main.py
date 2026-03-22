from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from app.config import get_settings
from app.database import engine, Base
from app.routers import bins, zones

settings = get_settings()
log      = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info('bin-registry starting')
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info('database tables ready')
    yield
    await engine.dispose()
    log.info('bin-registry stopped')


app = FastAPI(
    title='SMWCS Bin Registry',
    description='Bin, Zone and Sensor registry for SMWCS Kenya',
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

app.include_router(bins.router,  prefix='/api/v1/bins',  tags=['Bins'])
app.include_router(zones.router, prefix='/api/v1/zones', tags=['Zones'])


@app.get('/health')
async def health():
    return {'status': 'ok', 'service': settings.service_name}
