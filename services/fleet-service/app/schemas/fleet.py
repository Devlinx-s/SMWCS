from pydantic import BaseModel, Field, UUID4
from datetime import datetime, date
from typing import Optional
from app.models.fleet import TruckStatus, FuelType, DriverStatus, ShiftStatus


class LocationSchema(BaseModel):
    lat: float = Field(ge=-90,  le=90)
    lon: float = Field(ge=-180, le=180)


class TruckCreate(BaseModel):
    registration:    str
    capacity_kg:     int
    make:            Optional[str]      = None
    model:           Optional[str]      = None
    year:            Optional[int]      = None
    capacity_litres: Optional[int]      = None
    fuel_type:       FuelType           = FuelType.diesel
    gps_unit_id:     Optional[str]      = None


class TruckUpdate(BaseModel):
    status:             Optional[TruckStatus] = None
    current_load_kg:    Optional[int]         = None
    gps_unit_id:        Optional[str]         = None
    terminal_device_id: Optional[str]         = None
    odometer_km:        Optional[int]         = None


class TruckResponse(BaseModel):
    model_config = {'from_attributes': True}
    id:              UUID4
    registration:    str
    make:            Optional[str]
    model:           Optional[str]
    year:            Optional[int]
    capacity_kg:     int
    fuel_type:       FuelType
    status:          TruckStatus
    current_load_kg: int
    gps_unit_id:     Optional[str]
    created_at:      datetime


class DriverCreate(BaseModel):
    employee_id:    str
    first_name:     str
    last_name:      str
    phone:          Optional[str] = None
    email:          Optional[str] = None
    license_number: Optional[str] = None
    license_expiry: Optional[date] = None


class DriverUpdate(BaseModel):
    phone:          Optional[str]          = None
    email:          Optional[str]          = None
    license_number: Optional[str]          = None
    license_expiry: Optional[date]         = None
    status:         Optional[DriverStatus] = None


class DriverResponse(BaseModel):
    model_config = {'from_attributes': True}
    id:             UUID4
    employee_id:    str
    first_name:     str
    last_name:      str
    phone:          Optional[str]
    email:          Optional[str]
    license_number: Optional[str]
    license_expiry: Optional[date]
    status:         DriverStatus
    created_at:     datetime


class ShiftCreate(BaseModel):
    truck_id:      UUID4
    driver_id:     UUID4
    planned_start: datetime
    planned_end:   datetime
    notes:         Optional[str] = None


class ShiftResponse(BaseModel):
    model_config = {'from_attributes': True}
    id:            UUID4
    truck_id:      UUID4
    driver_id:     UUID4
    planned_start: datetime
    planned_end:   datetime
    actual_start:  Optional[datetime]
    actual_end:    Optional[datetime]
    status:        ShiftStatus
    notes:         Optional[str]
    created_at:    datetime
