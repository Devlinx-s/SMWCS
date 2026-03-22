from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from app.config import get_settings
from app.database import get_mongo_client, get_collection
from app.routers import auth, schedule, trucks, reports

settings = get_settings()
log      = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info('citizen-api starting')

    # Ensure MongoDB indexes
    col = get_collection('citizens')
    await col.create_index('email', unique=True)
    await col.create_index('location.zone_id')

    reports_col = get_collection('bin_reports')
    await reports_col.create_index('citizen_id')
    await reports_col.create_index('created_at')

    pickup_col = get_collection('pickup_requests')
    await pickup_col.create_index('citizen_id')

    log.info('citizen-api ready — MongoDB indexes created')
    yield
    log.info('citizen-api stopped')


app = FastAPI(
    title='SMWCS Citizen API',
    description='Citizen-facing API for SMWCS Kenya',
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

app.include_router(auth.router,     prefix='/api/v1/citizen',  tags=['Citizen Auth'])
app.include_router(schedule.router, prefix='/api/v1/citizen',  tags=['Schedule'])
app.include_router(trucks.router,   prefix='/api/v1/citizen',  tags=['Trucks'])
app.include_router(reports.router,  prefix='/api/v1/citizen',  tags=['Reports'])


@app.get('/health')
async def health():
    return {'status': 'ok', 'service': settings.service_name}
