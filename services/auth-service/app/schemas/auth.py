from pydantic import BaseModel, EmailStr, Field, UUID4
from datetime import datetime
from typing import Optional
from app.models.user import UserRole


class UserCreate(BaseModel):
    email:      EmailStr
    password:   str = Field(min_length=8)
    first_name: str
    last_name:  str
    role:       UserRole


class UserResponse(BaseModel):
    model_config = {'from_attributes': True}
    id:          UUID4
    email:       str
    first_name:  str
    last_name:   str
    role:        UserRole
    is_active:   bool
    mfa_enabled: bool
    last_login:  Optional[datetime]
    created_at:  datetime


class LoginRequest(BaseModel):
    email:     EmailStr
    password:  str
    totp_code: Optional[str] = None


class LoginResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = 'bearer'
    user:          UserResponse


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = 'bearer'


class MFASetupResponse(BaseModel):
    secret:  str
    qr_code: str


class MFAVerifyRequest(BaseModel):
    totp_code: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password:     str = Field(min_length=8)
