from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class SensorTelemetry(BaseModel):
    sensor_id:   str
    timestamp:   datetime
    fill_pct:    float    = Field(ge=0,   le=100)
    weight_kg:   float    = Field(ge=0,   le=500,  default=0)
    temp_c:      float    = Field(ge=-50, le=150,  default=25)
    battery_pct: int      = Field(ge=0,   le=100,  default=100)
    rssi:        int      = Field(ge=-120, le=0,   default=-70)
    waste_type:  str      = 'burnable'
    zone_id:     str      = 'unknown'
    gps_lat:     Optional[float] = None
    gps_lon:     Optional[float] = None


class TruckPosition(BaseModel):
    truck_id:  str
    timestamp: datetime
    lat:       float = Field(ge=-90,  le=90)
    lon:       float = Field(ge=-180, le=180)
    speed_kmh: float = Field(ge=0, le=200, default=0)
    heading:   float = Field(ge=0, le=360, default=0)
    load_kg:   int   = Field(ge=0, default=0)
    fuel_pct:  float = Field(ge=0, le=100, default=100)


class SensorAlert(BaseModel):
    sensor_id:  str
    timestamp:  datetime
    alert_type: str
    severity:   str = 'high'
    message:    str = ''
