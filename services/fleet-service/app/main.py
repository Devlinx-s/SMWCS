from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from app.config import get_settings
from app.database import engine, Base
from app.routers import trucks, drivers, shifts

settings = get_settings()
log      = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info('fleet-service starting')
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info('database tables ready')
    yield
    await engine.dispose()
    log.info('fleet-service stopped')


app = FastAPI(
    title='SMWCS Fleet Service',
    description='Truck, Driver and Shift management for SMWCS Kenya',
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

app.include_router(trucks.router,  prefix='/api/v1/trucks',  tags=['Trucks'])
app.include_router(drivers.router, prefix='/api/v1/drivers', tags=['Drivers'])
app.include_router(shifts.router,  prefix='/api/v1/shifts',  tags=['Shifts'])


@app.get('/health')
async def health():
    return {'status': 'ok', 'service': settings.service_name}
