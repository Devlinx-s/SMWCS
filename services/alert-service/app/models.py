import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Enum, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class AlertSeverity(str, enum.Enum):
    low      = 'low'
    medium   = 'medium'
    high     = 'high'
    critical = 'critical'


class AlertType(str, enum.Enum):
    bin_overflow       = 'bin_overflow'
    bin_fire           = 'bin_fire'
    bin_tamper         = 'bin_tamper'
    sensor_offline     = 'sensor_offline'
    sensor_low_battery = 'sensor_low_battery'
    truck_overload     = 'truck_overload'
    truck_breakdown    = 'truck_breakdown'
    truck_geofence     = 'truck_geofence'
    missed_stop        = 'missed_stop'
    driver_emergency   = 'driver_emergency'
    weather_warning    = 'weather_warning'


class Alert(Base):
    __tablename__ = 'alerts'

    id:               Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type:             Mapped[AlertType]       = mapped_column(Enum(AlertType), nullable=False)
    severity:         Mapped[AlertSeverity]   = mapped_column(Enum(AlertSeverity), nullable=False)
    sensor_id:        Mapped[str | None]      = mapped_column(String(64))
    truck_id:         Mapped[str | None]      = mapped_column(String(64))
    zone_id:          Mapped[str | None]      = mapped_column(String(64))
    message:          Mapped[str]             = mapped_column(Text, nullable=False)
    alert_metadata:   Mapped[dict | None]     = mapped_column(JSONB)
    acknowledged:     Mapped[bool]            = mapped_column(Boolean, default=False)
    acknowledged_by:  Mapped[str | None]      = mapped_column(String(64))
    acknowledged_at:  Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved:         Mapped[bool]            = mapped_column(Boolean, default=False)
    resolved_at:      Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_notes: Mapped[str | None]      = mapped_column(Text)
    created_at:       Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now())
