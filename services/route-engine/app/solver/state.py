import asyncio
from dataclasses import dataclass
from typing import Dict, List
import structlog

log = structlog.get_logger()


@dataclass
class BinState:
    sensor_id:  str
    fill_pct:   float
    lat:        float
    lon:        float
    zone_id:    str
    updated_at: str = ''


@dataclass
class TruckState:
    truck_id:    str
    lat:         float
    lon:         float
    load_kg:     int   = 0
    capacity_kg: int   = 3000
    is_available: bool = True


class ZoneStateManager:
    def __init__(self):
        self._bins:   Dict[str, BinState]   = {}
        self._trucks: Dict[str, TruckState] = {}
        self._lock = asyncio.Lock()

    async def update_bin(self, sensor_id: str, data: dict) -> None:
        async with self._lock:
            self._bins[sensor_id] = BinState(
                sensor_id  = sensor_id,
                fill_pct   = float(data.get('fill_pct', 0)),
                lat        = float(data.get('lat', 0.0)),
                lon        = float(data.get('lon', 0.0)),
                zone_id    = str(data.get('zone_id', 'unknown')),
                updated_at = str(data.get('timestamp', '')),
            )

    async def update_truck(self, truck_id: str, data: dict) -> None:
        async with self._lock:
            existing = self._trucks.get(truck_id)
            self._trucks[truck_id] = TruckState(
                truck_id     = truck_id,
                lat          = float(data.get('lat', 0.0)),
                lon          = float(data.get('lon', 0.0)),
                load_kg      = int(data.get('load_kg', 0)),
                capacity_kg  = int(data.get('capacity_kg', 3000)),
                is_available = existing.is_available if existing else True,
            )

    async def get_bins_for_zone(self, zone_id: str, min_fill_pct: float = 70.0) -> List[BinState]:
        async with self._lock:
            return [
                b for b in self._bins.values()
                if b.zone_id == zone_id and b.fill_pct >= min_fill_pct
            ]

    async def get_available_trucks(self) -> List[TruckState]:
        async with self._lock:
            return list(self._trucks.values()) or [
                # Fallback: use pilot truck if no GPS data yet
                TruckState(
                    truck_id    = 'b43d062c-a426-40f6-9404-3e19f9563a8a',
                    lat         = -1.2692,
                    lon         = 36.8090,
                    capacity_kg = 3000,
                    is_available= True,
                )
            ]


state_manager = ZoneStateManager()
