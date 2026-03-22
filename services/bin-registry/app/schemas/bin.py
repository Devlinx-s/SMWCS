from pydantic import BaseModel, Field, UUID4
from datetime import datetime, date
from typing import Optional
from app.models.bin import WasteType, BinStatus


class LocationSchema(BaseModel):
    lat: float = Field(ge=-90,  le=90)
    lon: float = Field(ge=-180, le=180)


class ZoneCreate(BaseModel):
    name:       str
    code:       str
    district:   Optional[str] = None
    population: Optional[int] = None
    boundary:   dict


class ZoneResponse(BaseModel):
    model_config = {'from_attributes': True}
    id:         UUID4
    name:       str
    code:       str
    district:   Optional[str]
    population: Optional[int]
    created_at: datetime


class BinCreate(BaseModel):
    serial_number:   str
    location:        LocationSchema
    zone_id:         Optional[UUID4] = None
    sensor_id:       Optional[str]   = None
    address:         Optional[str]   = None
    capacity_litres: int             = 120


class BinUpdate(BaseModel):
    zone_id:         Optional[UUID4]     = None
    sensor_id:       Optional[str]       = None
    address:         Optional[str]       = None
    status:          Optional[BinStatus] = None
    notes:           Optional[str]       = None
    capacity_litres: Optional[int]       = None


class BinResponse(BaseModel):
    model_config = {'from_attributes': True}
    id:              UUID4
    zone_id:         Optional[UUID4]
    sensor_id:       Optional[str]
    serial_number:   str
    address:         Optional[str]
    capacity_litres: int
    status:          BinStatus
    install_date:    Optional[date]
    last_serviced:   Optional[datetime]
    notes:           Optional[str]
    created_at:      datetime
    latest_fill_pct: Optional[float] = None


class BinFillSummary(BaseModel):
    zone_id:      str
    total:        int
    below_50:     int
    between_50_80: int
    above_80:     int
    critical:     int
