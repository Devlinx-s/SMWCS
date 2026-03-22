import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog
from app.config import get_settings
from app.database import engine, Base
from app.kafka.consumer import consume_loop
from app.routers import routes

settings = get_settings()
log      = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info('route-engine starting')
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    task = asyncio.create_task(consume_loop())
    log.info('route-engine ready — listening for bin events')
    yield
    task.cancel()
    await engine.dispose()
    log.info('route-engine stopped')


app = FastAPI(
    title='SMWCS Route Engine',
    description='CVRP route optimisation for SMWCS Kenya',
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

app.include_router(routes.router, prefix='/api/v1/routes', tags=['Routes'])


@app.get('/health')
async def health():
    return {'status': 'ok', 'service': settings.service_name}
