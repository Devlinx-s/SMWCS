import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, Enum, Float, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class RouteStatus(str, enum.Enum):
    pending   = 'pending'
    active    = 'active'
    completed = 'completed'
    cancelled = 'cancelled'


class Route(Base):
    __tablename__ = 'routes'

    id:           Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    truck_id:     Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    zone_id:      Mapped[str]             = mapped_column(String(64), nullable=False)
    shift_id:     Mapped[uuid.UUID | None]= mapped_column(UUID(as_uuid=True))
    status:       Mapped[RouteStatus]     = mapped_column(Enum(RouteStatus), default=RouteStatus.pending)
    total_stops:  Mapped[int]             = mapped_column(Integer, default=0)
    stops_done:   Mapped[int]             = mapped_column(Integer, default=0)
    generated_at: Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at:   Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RouteStop(Base):
    __tablename__ = 'route_stops'

    id:           Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    route_id:     Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), ForeignKey('routes.id'))
    bin_id:       Mapped[str]             = mapped_column(String(64), nullable=False)
    sensor_id:    Mapped[str | None]      = mapped_column(String(64))
    stop_order:   Mapped[int]             = mapped_column(Integer, nullable=False)
    fill_pct:     Mapped[float | None]    = mapped_column(Float)
    lat:          Mapped[float | None]    = mapped_column(Float)
    lon:          Mapped[float | None]    = mapped_column(Float)
    completed:    Mapped[bool]            = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rfid_scanned: Mapped[bool]            = mapped_column(Boolean, default=False)
    created_at:   Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now())
