from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timezone
import uuid
import structlog

from app.database import get_collection
from app.core.security import hash_password, verify_password, create_access_token
from app.core.deps import get_current_citizen, CurrentCitizen
from fastapi import Depends

log    = structlog.get_logger()
router = APIRouter()


class RegisterRequest(BaseModel):
    email:     EmailStr
    password:  str = Field(min_length=8)
    first_name: str
    last_name:  str
    phone:     str | None = None
    address:   str | None = None
    lat:       float | None = None
    lon:       float | None = None
    zone_id:   str | None = None


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type:   str = 'bearer'
    citizen_id:   str
    email:        str
    first_name:   str


@router.post('/register', response_model=AuthResponse, status_code=201)
async def register(data: RegisterRequest):
    col      = get_collection('citizens')
    existing = await col.find_one({'email': data.email})
    if existing:
        raise HTTPException(status_code=400, detail='Email already registered')

    citizen_id = str(uuid.uuid4())
    now        = datetime.now(timezone.utc).isoformat()

    doc = {
        '_id':        citizen_id,
        'email':      data.email,
        'password_hash': hash_password(data.password),
        'first_name': data.first_name,
        'last_name':  data.last_name,
        'phone':      data.phone,
        'address':    data.address,
        'location': {
            'lat':     data.lat,
            'lon':     data.lon,
            'zone_id': data.zone_id,
        } if data.lat else None,
        'recycling_score': 0,
        'created_at':  now,
        'updated_at':  now,
    }
    await col.insert_one(doc)
    log.info('citizen.registered', citizen_id=citizen_id, email=data.email)

    return AuthResponse(
        access_token=create_access_token(citizen_id, data.email),
        citizen_id=citizen_id,
        email=data.email,
        first_name=data.first_name,
    )


@router.post('/login', response_model=AuthResponse)
async def login(data: LoginRequest):
    col     = get_collection('citizens')
    citizen = await col.find_one({'email': data.email})

    if not citizen or not verify_password(data.password, citizen['password_hash']):
        raise HTTPException(
            status_code=401,
            detail='Incorrect email or password',
        )

    return AuthResponse(
        access_token=create_access_token(citizen['_id'], citizen['email']),
        citizen_id=citizen['_id'],
        email=citizen['email'],
        first_name=citizen['first_name'],
    )


@router.get('/me')
async def get_me(citizen: CurrentCitizen = Depends(get_current_citizen)):
    col = get_collection('citizens')
    doc = await col.find_one({'_id': citizen.citizen_id})
    if not doc:
        raise HTTPException(status_code=404, detail='Citizen not found')
    doc.pop('password_hash', None)
    return doc
