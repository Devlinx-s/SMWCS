from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from app.config import get_settings
from app.database import engine, Base
from app.routers import auth, users

settings = get_settings()
log      = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info('auth-service starting')
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info('database tables ready')
    yield
    await engine.dispose()
    log.info('auth-service stopped')


app = FastAPI(
    title='SMWCS Auth Service',
    description='Authentication for Smart Municipal Waste Collection System — Kenya',
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

app.include_router(auth.router,  prefix='/api/v1/auth',  tags=['Authentication'])
app.include_router(users.router, prefix='/api/v1/users', tags=['Users'])


@app.get('/health')
async def health():
    return {'status': 'ok', 'service': settings.service_name}
