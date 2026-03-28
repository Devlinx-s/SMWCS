# Remaining Work
## SMWCS — Implementation Guide for TODO Services

**Current version:** 0.3.0  
**Services complete:** auth, bin-registry, fleet-service, iot-ingestion, alert-service, command-api, dashboard  
**Services remaining:** route-engine, driver-terminal, citizen-api, analytics-service, media-service  
**Apps remaining:** driver-terminal-app (React Native), citizen-app (React Native)

Read this file before building any of the remaining services.
Each section covers: what it does, how to set it up, every file to create, and how to test it.

---

## Build Order

Build in this exact order — each service depends on the one before it:

```
1. route-engine          ← depends on: Kafka (bin.sensor.reading), OSRM, PostgreSQL
2. driver-terminal       ← depends on: route-engine (route.updated), PostgreSQL
3. citizen-api           ← depends on: MongoDB, Kafka
4. analytics-service     ← depends on: PostgreSQL, Redis (Celery broker)
5. media-service         ← depends on: MinIO
6. driver-terminal-app   ← depends on: driver-terminal WebSocket
7. citizen-app           ← depends on: citizen-api
```

---

## 1. Route Engine (port 8004)

### What it does
The route engine is the brain of the system. It:
1. Listens to Kafka for bin fill level updates
2. Maintains in-memory state of all bin fill levels and truck positions per zone
3. Every 5 minutes (or immediately on a critical fill event) runs a CVRP solver
4. The solver uses OR-Tools to assign bins to trucks with optimal routes
5. Gets real road distances from OSRM (OpenStreetMap routing)
6. Publishes the resulting routes to Kafka as `route.updated`

### Prerequisites — OSRM setup (do this first)

```bash
cd ~/git/SMWCS/infrastructure
mkdir -p osrm
cd osrm

# Download Kenya OSM data (~100MB, takes a few minutes)
wget https://download.geofabrik.de/africa/kenya-latest.osm.pbf

# Pre-process step 1: extract road network (takes 5–10 minutes)
docker run -t -v $(pwd):/data osrm/osrm-backend \
  osrm-extract -p /opt/car.lua /data/kenya-latest.osm.pbf

# Pre-process step 2: partition
docker run -t -v $(pwd):/data osrm/osrm-backend \
  osrm-partition /data/kenya-latest.osrm

# Pre-process step 3: customize
docker run -t -v $(pwd):/data osrm/osrm-backend \
  osrm-customize /data/kenya-latest.osrm

# Start OSRM server (keep running in background)
docker run -d --name smwcs_osrm \
  -p 5000:5000 \
  -v $(pwd):/data \
  osrm/osrm-backend \
  osrm-routed --algorithm mld /data/kenya-latest.osrm

# Test it — route from Nairobi CBD to Westlands
curl "http://localhost:5000/route/v1/driving/36.8219,-1.2921;36.8089,-1.2634"
# Should return JSON with routes array
```

Also add OSRM to `docker-compose.yml` for permanence:
```yaml
osrm:
  image: osrm/osrm-backend:latest
  container_name: smwcs_osrm
  restart: unless-stopped
  ports:
    - "5000:5000"
  volumes:
    - ./infrastructure/osrm:/data
  command: osrm-routed --algorithm mld /data/kenya-latest.osrm
```

### Setup

```bash
cd ~/git/SMWCS/services/route-engine

poetry init \
  --name route-engine \
  --description "SMWCS Route Optimisation Engine" \
  --python "^3.11" \
  --no-interaction

poetry add \
  fastapi \
  "uvicorn[standard]" \
  pydantic \
  pydantic-settings \
  "sqlalchemy[asyncio]" \
  asyncpg \
  confluent-kafka \
  httpx \
  ortools \
  numpy \
  "python-jose[cryptography]" \
  structlog \
  prometheus-client \
  python-dotenv \
  tenacity

poetry add --group dev pytest pytest-asyncio ruff
```

### Folder structure

```
services/route-engine/
  app/
    __init__.py
    config.py
    database.py
    models.py          ← Route, RouteStop SQLAlchemy models
    schemas.py         ← Pydantic schemas for routes
    core/
      deps.py          ← RBAC (copy from auth-service)
    solver/
      __init__.py
      cvrp.py          ← OR-Tools CVRP solver
      distance.py      ← OSRM distance matrix builder
      state.py         ← ZoneStateManager in-memory state
    routers/
      routes.py        ← GET /api/v1/routes/active, GET /api/v1/routes/{id}
    kafka/
      consumer.py      ← Kafka consumer loop
      publisher.py     ← Publish route.updated
    main.py
  .env
```

### File: app/models.py

```python
import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, Enum, Text, Float, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class RouteStatus(str, enum.Enum):
    pending   = 'pending'
    active    = 'active'
    completed = 'completed'
    cancelled = 'cancelled'

class Route(Base):
    __tablename__ = 'routes'
    id:           Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    truck_id:     Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    zone_id:      Mapped[str]            = mapped_column(String(64), nullable=False)
    shift_id:     Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True))
    status:       Mapped[RouteStatus]    = mapped_column(Enum(RouteStatus), default=RouteStatus.pending)
    total_stops:  Mapped[int]            = mapped_column(Integer, default=0)
    stops_done:   Mapped[int]            = mapped_column(Integer, default=0)
    generated_at: Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at:   Mapped[datetime|None]  = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime|None]  = mapped_column(DateTime(timezone=True))

class RouteStop(Base):
    __tablename__ = 'route_stops'
    id:           Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    route_id:     Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey('routes.id'))
    bin_id:       Mapped[str]            = mapped_column(String(64), nullable=False)
    sensor_id:    Mapped[str|None]       = mapped_column(String(64))
    stop_order:   Mapped[int]            = mapped_column(Integer, nullable=False)
    fill_pct:     Mapped[float|None]     = mapped_column(Float)
    completed:    Mapped[bool]           = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime|None]  = mapped_column(DateTime(timezone=True))
    rfid_scanned: Mapped[bool]           = mapped_column(Boolean, default=False)
    created_at:   Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now())
```

### File: app/solver/state.py

```python
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List
import structlog

log = structlog.get_logger()

@dataclass
class BinState:
    sensor_id:  str
    bin_id:     str
    fill_pct:   float
    lat:        float
    lon:        float
    zone_id:    str
    updated_at: str

@dataclass
class TruckState:
    truck_id:    str
    lat:         float
    lon:         float
    load_kg:     int
    capacity_kg: int
    is_available: bool

class ZoneStateManager:
    """In-memory state of all bin fill levels and truck positions."""

    def __init__(self):
        self._bins:   Dict[str, BinState]  = {}   # sensor_id → BinState
        self._trucks: Dict[str, TruckState]= {}   # truck_id  → TruckState
        self._lock = asyncio.Lock()

    async def update_bin(self, sensor_id: str, data: dict) -> None:
        async with self._lock:
            self._bins[sensor_id] = BinState(
                sensor_id  = sensor_id,
                bin_id     = data.get('bin_id', sensor_id),
                fill_pct   = data['fill_pct'],
                lat        = data.get('lat', 0.0),
                lon        = data.get('lon', 0.0),
                zone_id    = data.get('zone_id', 'unknown'),
                updated_at = data.get('timestamp', ''),
            )

    async def update_truck(self, truck_id: str, data: dict) -> None:
        async with self._lock:
            existing = self._trucks.get(truck_id)
            self._trucks[truck_id] = TruckState(
                truck_id     = truck_id,
                lat          = data.get('lat', 0.0),
                lon          = data.get('lon', 0.0),
                load_kg      = data.get('load_kg', 0),
                capacity_kg  = data.get('capacity_kg', 3000),
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
            return [t for t in self._trucks.values() if t.is_available]

# Singleton
state_manager = ZoneStateManager()
```

### File: app/solver/distance.py

```python
import httpx
import structlog
from app.config import get_settings

settings = get_settings()
log      = structlog.get_logger()

async def build_distance_matrix(locations: list[tuple[float, float]]) -> list[list[float]]:
    """
    Call OSRM Table API to get travel time matrix.
    locations: list of (lat, lon) tuples
    Returns: NxN matrix of travel times in seconds
    """
    if len(locations) < 2:
        return [[0]]

    # OSRM expects lon,lat order
    coords = ';'.join(f'{lon},{lat}' for lat, lon in locations)
    url    = f'{settings.osrm_base_url}/table/v1/driving/{coords}'

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params={'annotations': 'duration'})
            response.raise_for_status()
            data = response.json()

            if data.get('code') != 'Ok':
                log.error('osrm.table.failed', code=data.get('code'))
                # Return fallback Euclidean distance matrix
                return _euclidean_fallback(locations)

            return data['durations']  # NxN matrix in seconds

    except Exception as e:
        log.error('osrm.request.failed', error=str(e))
        return _euclidean_fallback(locations)


def _euclidean_fallback(locations: list[tuple[float, float]]) -> list[list[float]]:
    """Simple straight-line distance fallback if OSRM is unavailable."""
    import math
    n = len(locations)
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                lat1, lon1 = locations[i]
                lat2, lon2 = locations[j]
                # Rough km distance × 120 seconds/km (30 km/h average)
                dist = math.sqrt((lat2-lat1)**2 + (lon2-lon1)**2) * 111 * 120
                matrix[i][j] = dist
    return matrix
```

### File: app/solver/cvrp.py

```python
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import structlog
from app.solver.state import BinState, TruckState

log = structlog.get_logger()

COLLECTION_THRESHOLD_PCT = 70.0  # only include bins above this fill level

def solve_cvrp(
    bins:            list[BinState],
    trucks:          list[TruckState],
    distance_matrix: list[list[float]],
) -> dict[str, list[str]]:
    """
    Solve Capacitated Vehicle Routing Problem.
    Returns: dict of truck_id → ordered list of sensor_ids to visit
    """
    if not bins or not trucks:
        return {}

    n_locations = len(bins) + 1  # +1 for depot (waste station)
    n_vehicles   = len(trucks)

    # Depot is index 0, bins are indices 1..n
    def distance_callback(from_idx, to_idx):
        from_node = manager.IndexToNode(from_idx)
        to_node   = manager.IndexToNode(to_idx)
        return int(distance_matrix[from_node][to_node])

    manager = pywrapcp.RoutingIndexManager(n_locations, n_vehicles, 0)
    routing = pywrapcp.RoutingModel(manager)

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Capacity constraint — using fill percentage as demand proxy
    def demand_callback(from_idx):
        from_node = manager.IndexToNode(from_idx)
        if from_node == 0:
            return 0  # depot
        return int(bins[from_node - 1].fill_pct)  # demand proportional to fill

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,            # no slack
        [300] * n_vehicles,  # max demand per vehicle (300 = full truck = sum of 3 full bins)
        True,         # start cumul to zero
        'Capacity',
    )

    # Search parameters
    search_params = pywrapcp.DefaultRoutingSearchParameters()
    search_params.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_params.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_params.time_limit.seconds = 10  # max 10 seconds to solve

    solution = routing.SolveWithParameters(search_params)

    if not solution:
        log.warning('cvrp.no_solution_found', n_bins=len(bins), n_trucks=n_vehicles)
        return {}

    result = {}
    for vehicle_idx in range(n_vehicles):
        truck_id = trucks[vehicle_idx].truck_id
        route    = []
        index    = routing.Start(vehicle_idx)
        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            if node != 0:  # skip depot
                route.append(bins[node - 1].sensor_id)
            index = solution.Value(routing.NextVar(index))
        if route:
            result[truck_id] = route
            log.info('cvrp.route_assigned',
                     truck_id=truck_id,
                     stops=len(route),
                     total_fill=sum(b.fill_pct for b in bins if b.sensor_id in route))

    return result
```

### File: app/kafka/consumer.py

```python
import asyncio
import json
import structlog
from datetime import datetime, timezone
from confluent_kafka import Consumer, KafkaError
from app.config import get_settings
from app.solver.state import state_manager
from app.solver.cvrp import solve_cvrp
from app.solver.distance import build_distance_matrix
from app.kafka.publisher import publish_route_updated

settings = get_settings()
log      = structlog.get_logger()

# Track last optimisation time per zone to throttle re-runs
_last_optimised: dict[str, datetime] = {}
OPTIMISE_INTERVAL_SECONDS = 300  # 5 minutes


async def should_optimise(zone_id: str, force: bool = False) -> bool:
    if force:
        return True
    last = _last_optimised.get(zone_id)
    if last is None:
        return True
    elapsed = (datetime.now(timezone.utc) - last).total_seconds()
    return elapsed >= OPTIMISE_INTERVAL_SECONDS


async def run_optimisation_for_zone(zone_id: str) -> None:
    bins   = await state_manager.get_bins_for_zone(zone_id, min_fill_pct=70.0)
    trucks = await state_manager.get_available_trucks()

    if not bins:
        log.info('route.no_bins_to_collect', zone_id=zone_id)
        return
    if not trucks:
        log.warning('route.no_trucks_available', zone_id=zone_id)
        return

    # Build location list: depot first (approximate Nairobi waste station), then bins
    depot = (-1.3031, 36.8303)  # Ruai landfill approximate location
    locations = [depot] + [(b.lat, b.lon) for b in bins]

    distance_matrix = await build_distance_matrix(locations)
    routes          = solve_cvrp(bins, trucks, distance_matrix)

    _last_optimised[zone_id] = datetime.now(timezone.utc)

    for truck_id, stop_sensor_ids in routes.items():
        await publish_route_updated(truck_id, zone_id, stop_sensor_ids, bins)


async def consume_loop() -> None:
    consumer = Consumer({
        'bootstrap.servers':  settings.kafka_brokers,
        'group.id':           'route-engine',
        'auto.offset.reset':  'latest',
        'enable.auto.commit': True,
    })

    consumer.subscribe(['bin.sensor.reading', 'bin.fill.critical', 'truck.position'])
    log.info('route-engine.kafka.started')
    loop = asyncio.get_event_loop()

    try:
        while True:
            msg = await loop.run_in_executor(None, consumer.poll, 1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() != KafkaError._PARTITION_EOF:
                    log.error('kafka.error', error=str(msg.error()))
                continue

            try:
                value = json.loads(msg.value().decode('utf-8'))
                topic = msg.topic()

                if topic == 'bin.sensor.reading':
                    sensor_id = value.get('sensor_id', '')
                    zone_id   = value.get('zone_id', '')
                    await state_manager.update_bin(sensor_id, value)
                    if await should_optimise(zone_id):
                        asyncio.create_task(run_optimisation_for_zone(zone_id))

                elif topic == 'bin.fill.critical':
                    zone_id = value.get('zone_id', '')
                    await state_manager.update_bin(value.get('sensor_id', ''), value)
                    # Force immediate re-optimisation on critical fill
                    asyncio.create_task(run_optimisation_for_zone(zone_id))
                    log.warning('route.critical_fill_reoptimise', zone_id=zone_id)

                elif topic == 'truck.position':
                    truck_id = value.get('truck_id', '')
                    await state_manager.update_truck(truck_id, value)

            except Exception as e:
                log.error('route.message.failed', error=str(e))
    finally:
        consumer.close()
```

### File: app/kafka/publisher.py

```python
import json
import uuid
from datetime import datetime, timezone
from confluent_kafka import Producer
from app.config import get_settings
import structlog

settings = get_settings()
log      = structlog.get_logger()
_producer = None

def get_producer() -> Producer:
    global _producer
    if _producer is None:
        _producer = Producer({'bootstrap.servers': settings.kafka_brokers})
    return _producer

async def publish_route_updated(
    truck_id:        str,
    zone_id:         str,
    stop_sensor_ids: list[str],
    bins:            list,
) -> None:
    stops = []
    for order, sensor_id in enumerate(stop_sensor_ids):
        bin_state = next((b for b in bins if b.sensor_id == sensor_id), None)
        stops.append({
            'stop_order': order + 1,
            'sensor_id':  sensor_id,
            'fill_pct':   bin_state.fill_pct if bin_state else None,
            'lat':        bin_state.lat if bin_state else None,
            'lon':        bin_state.lon if bin_state else None,
        })

    payload = {
        'route_id':     str(uuid.uuid4()),
        'truck_id':     truck_id,
        'zone_id':      zone_id,
        'stops':        stops,
        'total_stops':  len(stops),
        'generated_at': datetime.now(timezone.utc).isoformat(),
    }

    try:
        get_producer().produce(
            'route.updated',
            key=truck_id,
            value=json.dumps(payload, default=str),
        )
        get_producer().poll(0)
        log.info('route.published', truck_id=truck_id, stops=len(stops))
    except Exception as e:
        log.error('route.publish.failed', error=str(e))
```

### File: app/main.py

```python
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
    log.info('route-engine ready')
    yield
    task.cancel()
    await engine.dispose()

app = FastAPI(title='SMWCS Route Engine', version='1.0.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
app.include_router(routes.router, prefix='/api/v1/routes', tags=['Routes'])

@app.get('/health')
async def health():
    return {'status': 'ok', 'service': settings.service_name}
```

### File: .env

```env
SERVICE_NAME=route-engine
SERVICE_PORT=8004
DEBUG=true
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DB=smwcs
POSTGRES_USER=smwcs
POSTGRES_PASSWORD=smwcs_dev_pass
KAFKA_BROKERS=localhost:9092
OSRM_BASE_URL=http://localhost:5000
JWT_SECRET=smwcs-jwt-secret
JWT_ALGORITHM=HS256
```

### Run

```bash
poetry run uvicorn app.main:app --reload --port 8004
```

### Test

```bash
# Send a bin reading to trigger route calculation
mosquitto_pub -h localhost -p 1883 \
  -t "smwcs/sensors/SN-NBI-001/telemetry" \
  -m '{"fill_pct": 85.0, "lat": -1.2692, "lon": 36.8090, "zone_id": "bc2437c2-..."}'

# Watch route-engine logs for:
# cvrp.route_assigned  truck_id=...  stops=N
# route.published      truck_id=...  stops=N

# Consume route.updated from Kafka to verify
docker exec smwcs_kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic route.updated \
  --from-beginning
```

---

## 2. Driver Terminal Service (port 8005)

### What it does
WebSocket server that truck drivers' Android tablets connect to.
- On connect: sends the full current route (ROUTE_FULL)
- When route-engine updates a route: sends delta (ROUTE_DELTA)
- Receives: STOP_COMPLETED, RFID_SCAN, DRIVER_EMERGENCY from the tablet
- On emergency: creates a critical alert immediately

### Setup

```bash
cd ~/git/SMWCS/services/driver-terminal

poetry init --name driver-terminal --python "^3.11" --no-interaction

poetry add \
  fastapi \
  "uvicorn[standard]" \
  pydantic \
  pydantic-settings \
  "sqlalchemy[asyncio]" \
  asyncpg \
  confluent-kafka \
  "python-jose[cryptography]" \
  structlog \
  python-dotenv

mkdir -p app/{routers,services,core}
touch app/__init__.py app/routers/__init__.py app/services/__init__.py app/core/__init__.py
```

### File: app/services/connection_manager.py

```python
from fastapi import WebSocket
from typing import Dict
import json
import structlog

log = structlog.get_logger()

class TerminalConnectionManager:
    """Maps truck_id → WebSocket connection."""

    def __init__(self):
        self._connections: Dict[str, WebSocket] = {}

    async def connect(self, truck_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._connections[truck_id] = ws
        log.info('terminal.connected', truck_id=truck_id, total=len(self._connections))

    def disconnect(self, truck_id: str) -> None:
        self._connections.pop(truck_id, None)
        log.info('terminal.disconnected', truck_id=truck_id)

    async def send(self, truck_id: str, message: dict) -> bool:
        ws = self._connections.get(truck_id)
        if not ws:
            return False
        try:
            await ws.send_text(json.dumps(message, default=str))
            return True
        except Exception as e:
            log.error('terminal.send.failed', truck_id=truck_id, error=str(e))
            self.disconnect(truck_id)
            return False

    async def broadcast(self, message: dict) -> None:
        for truck_id in list(self._connections.keys()):
            await self.send(truck_id, message)

    @property
    def connected_trucks(self) -> list[str]:
        return list(self._connections.keys())

manager = TerminalConnectionManager()
```

### File: app/routers/terminal.py

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime, timezone
import json
import structlog
from app.database import get_db
from app.services.connection_manager import manager
from app.kafka.publisher import publish

log    = structlog.get_logger()
router = APIRouter()

@router.websocket('/ws/terminal/{truck_id}')
async def terminal_ws(truck_id: str, ws: WebSocket, db: AsyncSession = Depends(get_db)):
    # AUTH: validate terminal token from query param
    token = ws.query_params.get('token')
    if not token:
        await ws.close(code=4001, reason='Token required')
        return

    # TODO: validate token against Redis terminal tokens
    # For now accept any non-empty token in dev
    await manager.connect(truck_id, ws)

    # Send current route on connect (ROUTE_FULL)
    result = await db.execute(text("""
        SELECT r.id, r.zone_id, json_agg(
            json_build_object(
                'stop_order', rs.stop_order,
                'bin_id',     rs.bin_id,
                'sensor_id',  rs.sensor_id,
                'fill_pct',   rs.fill_pct,
                'completed',  rs.completed
            ) ORDER BY rs.stop_order
        ) AS stops
        FROM routes r
        JOIN route_stops rs ON rs.route_id = r.id
        WHERE r.truck_id = :truck_id AND r.status = 'active'
        GROUP BY r.id, r.zone_id
        LIMIT 1
    """), {'truck_id': truck_id})
    route = result.mappings().first()

    if route:
        await ws.send_text(json.dumps({
            'type':  'ROUTE_FULL',
            'route': dict(route),
        }, default=str))

    try:
        while True:
            data = json.loads(await ws.receive_text())
            msg_type = data.get('type')

            if msg_type == 'STOP_COMPLETED':
                stop_id = data.get('stop_id')
                await db.execute(text("""
                    UPDATE route_stops
                    SET completed = true, completed_at = :now
                    WHERE id = :id
                """), {'id': stop_id, 'now': datetime.now(timezone.utc)})
                await db.execute(text("""
                    UPDATE routes SET stops_done = stops_done + 1
                    WHERE id = (SELECT route_id FROM route_stops WHERE id = :id)
                """), {'id': stop_id})
                await db.commit()
                publish('stop.completed', truck_id, {'truck_id': truck_id, 'stop_id': stop_id})
                log.info('stop.completed', truck_id=truck_id, stop_id=stop_id)

            elif msg_type == 'RFID_SCAN':
                bin_id = data.get('bin_id')
                log.info('rfid.scan', truck_id=truck_id, bin_id=bin_id)
                # Confirm stop via RFID
                await ws.send_text(json.dumps({
                    'type':   'RFID_CONFIRMED',
                    'bin_id': bin_id,
                }))

            elif msg_type == 'DRIVER_EMERGENCY':
                lat = data.get('lat')
                lon = data.get('lon')
                publish('alert.driver', truck_id, {
                    'truck_id':   truck_id,
                    'alert_type': 'driver_emergency',
                    'severity':   'critical',
                    'lat':        lat,
                    'lon':        lon,
                    'timestamp':  datetime.now(timezone.utc).isoformat(),
                })
                log.error('driver.emergency', truck_id=truck_id, lat=lat, lon=lon)

            elif msg_type == 'ping':
                await ws.send_text(json.dumps({'type': 'pong'}))

    except WebSocketDisconnect:
        manager.disconnect(truck_id)
    except Exception as e:
        log.error('terminal.ws.error', truck_id=truck_id, error=str(e))
        manager.disconnect(truck_id)
```

### Kafka consumer for route.updated

Add a background task in `main.py` that consumes `route.updated` and pushes `ROUTE_DELTA` to the relevant truck's WebSocket.

```python
# In app/kafka/route_consumer.py
async def route_update_worker() -> None:
    consumer = Consumer({
        'bootstrap.servers': settings.kafka_brokers,
        'group.id':          'driver-terminal',
        'auto.offset.reset': 'latest',
    })
    consumer.subscribe(['route.updated', 'alert.driver'])
    loop = asyncio.get_event_loop()

    while True:
        msg = await loop.run_in_executor(None, consumer.poll, 0.5)
        if msg is None or msg.error():
            continue
        value    = json.loads(msg.value().decode())
        truck_id = value.get('truck_id', '')

        if msg.topic() == 'route.updated':
            await manager.send(truck_id, {'type': 'ROUTE_DELTA', 'route': value})

        elif msg.topic() == 'alert.driver':
            await manager.send(truck_id, {'type': 'DRIVER_ALERT', 'alert': value})
```

### .env

```env
SERVICE_NAME=driver-terminal
SERVICE_PORT=8005
DEBUG=true
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DB=smwcs
POSTGRES_USER=smwcs
POSTGRES_PASSWORD=smwcs_dev_pass
KAFKA_BROKERS=localhost:9092
JWT_SECRET=smwcs-jwt-secret
JWT_ALGORITHM=HS256
```

### Test

```bash
# Test WebSocket connection using wscat (install: npm i -g wscat)
wscat -c "ws://localhost:8005/ws/terminal/b43d062c-...?token=test"

# You should receive ROUTE_FULL with current stops
# Then in another terminal publish a route update:
docker exec smwcs_kafka kafka-console-producer \
  --bootstrap-server localhost:9092 \
  --topic route.updated \
  --property "parse.key=true" --property "key.separator=:"
# type: b43d062c-...:{"truck_id":"b43d062c-...","stops":[...]}
# The WebSocket should receive ROUTE_DELTA
```

---

## 3. Citizen API (port 8008)

### What it does
REST API for the citizen mobile app. Uses MongoDB for citizen data
(not PostgreSQL) because citizen records are document-oriented and
don't need relational joins.

### Setup

```bash
cd ~/git/SMWCS/services/citizen-api

poetry init --name citizen-api --python "^3.11" --no-interaction

poetry add \
  fastapi \
  "uvicorn[standard]" \
  pydantic \
  pydantic-settings \
  motor \
  confluent-kafka \
  "python-jose[cryptography]" \
  "passlib[bcrypt]" \
  "pydantic[email]" \
  "bcrypt==4.0.1" \
  structlog \
  python-dotenv

mkdir -p app/{routers,models,services}
touch app/__init__.py app/routers/__init__.py
```

### MongoDB collections

```
citizens         email (unique), password_hash, address {lat, lon, zone_id}, created_at
bin_reports      citizen_id, bin_id, photo_url, description, status, created_at
pickup_requests  citizen_id, item_type, photo_url, address, requested_date, status, created_at
```

### Endpoints to build

```python
# app/routers/auth.py
POST /api/v1/citizen/register      # email, password, address (lat/lon)
POST /api/v1/citizen/login         # returns JWT

# app/routers/schedule.py
GET  /api/v1/citizen/schedule      # zone-based collection calendar next 30 days
                                   # reads from PostgreSQL zones + static schedule config

# app/routers/trucks.py
GET  /api/v1/citizen/truck-eta     # nearest active truck in citizen's zone + ETA
                                   # queries fleet-service via HTTP (or shared PostgreSQL)

# app/routers/reports.py
POST /api/v1/citizen/report-bin    # photo + GPS pin + description
                                   # writes to MongoDB bin_reports
                                   # publishes bin.citizen.report to Kafka
                                   # alert-service creates an alert from it

# app/routers/pickup.py
POST /api/v1/citizen/pickup-request  # special item pickup
                                     # date picker, item type, photo

# app/routers/classify.py
POST /api/v1/citizen/classify-waste  # image upload → TensorFlow waste classifier
                                     # returns: burnable/recyclable/organic/hazardous
```

### Waste classifier

The waste classifier uses a pre-trained MobileNetV2 model fine-tuned on waste categories.

```bash
# Install TensorFlow (heavy — do separately)
poetry add tensorflow pillow

# Model file goes in: services/citizen-api/models/waste_classifier.keras
# Training data categories: burnable, non_burnable, recyclable, organic, hazardous, electronic
```

```python
# app/services/classifier.py
import numpy as np
from PIL import Image
import io

_model = None

def get_model():
    global _model
    if _model is None:
        import tensorflow as tf
        _model = tf.keras.models.load_model('models/waste_classifier.keras')
    return _model

LABELS = ['burnable', 'electronic', 'hazardous', 'non_burnable', 'organic', 'recyclable']

async def classify_image(image_bytes: bytes) -> dict:
    img = Image.open(io.BytesIO(image_bytes)).resize((224, 224))
    arr = np.array(img) / 255.0
    arr = np.expand_dims(arr, axis=0)
    predictions = get_model().predict(arr)[0]
    top_idx     = int(np.argmax(predictions))
    return {
        'category':   LABELS[top_idx],
        'confidence': float(predictions[top_idx]),
        'all':        dict(zip(LABELS, [float(p) for p in predictions])),
    }
```

### .env

```env
SERVICE_NAME=citizen-api
SERVICE_PORT=8008
DEBUG=true
MONGO_URI=mongodb://localhost:27018
MONGO_DB=smwcs_citizen
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DB=smwcs
POSTGRES_USER=smwcs
POSTGRES_PASSWORD=smwcs_dev_pass
KAFKA_BROKERS=localhost:9092
JWT_SECRET=smwcs-citizen-jwt-secret
JWT_ALGORITHM=HS256
```

---

## 4. Analytics Service (background — no HTTP)

### What it does
Celery worker that runs scheduled background jobs:
- Every hour: aggregate zone fill statistics
- Every day at midnight: compute driver KPIs (stops, idle time, route adherence)
- Every week: generate zone collection report

### Setup

```bash
cd ~/git/SMWCS/services/analytics-service

poetry init --name analytics-service --python "^3.11" --no-interaction

poetry add \
  celery \
  "celery[redis]" \
  "sqlalchemy[asyncio]" \
  asyncpg \
  psycopg2-binary \
  pydantic-settings \
  structlog \
  python-dotenv

mkdir -p app/tasks
touch app/__init__.py app/tasks/__init__.py
```

### File: app/celery_app.py

```python
from celery import Celery
from celery.schedules import crontab
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    'smwcs-analytics',
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.timezone = 'Africa/Nairobi'

celery_app.conf.beat_schedule = {
    'hourly-zone-aggregation': {
        'task':     'app.tasks.aggregation.aggregate_zone_hourly',
        'schedule': crontab(minute=0),  # every hour on the hour
    },
    'daily-driver-kpis': {
        'task':     'app.tasks.driver_kpis.compute_driver_kpis',
        'schedule': crontab(hour=0, minute=5),  # every day at 00:05 Nairobi time
    },
    'weekly-zone-report': {
        'task':     'app.tasks.reports.generate_zone_weekly_report',
        'schedule': crontab(day_of_week=1, hour=6, minute=0),  # Monday 06:00
    },
}
```

### File: app/tasks/aggregation.py

```python
from app.celery_app import celery_app
import psycopg2
from app.config import get_settings
import structlog

settings = get_settings()
log      = structlog.get_logger()

@celery_app.task(name='app.tasks.aggregation.aggregate_zone_hourly')
def aggregate_zone_hourly():
    """
    Count bins by fill tier per zone and write to analytics.zone_hourly table.
    Reads from: bins table (status + latest fill from InfluxDB)
    Writes to:  analytics_zone_hourly table
    """
    conn = psycopg2.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        dbname=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
    )
    cursor = conn.cursor()

    # Create analytics table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analytics_zone_hourly (
            id          SERIAL PRIMARY KEY,
            zone_id     UUID NOT NULL,
            zone_name   VARCHAR(100),
            recorded_at TIMESTAMPTZ DEFAULT now(),
            total_bins  INTEGER DEFAULT 0,
            below_50    INTEGER DEFAULT 0,
            between_50_80 INTEGER DEFAULT 0,
            above_80    INTEGER DEFAULT 0,
            critical    INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        SELECT z.id, z.name, COUNT(b.id) as total
        FROM zones z
        LEFT JOIN bins b ON b.zone_id = z.id AND b.status = 'active'
        GROUP BY z.id, z.name
    """)
    zones = cursor.fetchall()

    for zone_id, zone_name, total in zones:
        cursor.execute("""
            INSERT INTO analytics_zone_hourly (zone_id, zone_name, total_bins)
            VALUES (%s, %s, %s)
        """, (zone_id, zone_name, total))

    conn.commit()
    conn.close()
    log.info('analytics.zone_hourly.done', zones=len(zones))
```

### Running Celery (CRITICAL — only 1 beat instance ever)

```bash
# Terminal 1: Celery worker (can scale to multiple)
cd ~/git/SMWCS/services/analytics-service
poetry run celery -A app.celery_app worker --loglevel=info --concurrency=2

# Terminal 2: Celery beat scheduler (NEVER run more than 1 instance)
poetry run celery -A app.celery_app beat --loglevel=info

# View scheduled tasks
poetry run celery -A app.celery_app inspect scheduled
```

### .env

```env
SERVICE_NAME=analytics-service
DEBUG=true
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DB=smwcs
POSTGRES_USER=smwcs
POSTGRES_PASSWORD=smwcs_dev_pass
REDIS_URL=redis://:smwcs_dev_pass@127.0.0.1:6379
```

---

## 5. Media Service (port 8012)

### What it does
Handles image uploads (bin photos, report photos, special pickup photos).
Compresses images with Pillow before storing in MinIO.
Returns a public CDN URL.

### Setup

```bash
cd ~/git/SMWCS/services/media-service

poetry init --name media-service --python "^3.11" --no-interaction

poetry add \
  fastapi \
  "uvicorn[standard]" \
  pydantic-settings \
  aioboto3 \
  pillow \
  python-multipart \
  structlog \
  python-dotenv
```

### Key endpoint

```python
# POST /api/v1/media/upload
# Accepts: multipart/form-data with file field
# Returns: {"url": "http://localhost:9000/smwcs/images/abc123.jpg"}

@router.post('/upload')
async def upload(file: UploadFile = File(...)):
    contents = await file.read()

    # Compress with Pillow
    img = Image.open(io.BytesIO(contents))
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    img.thumbnail((1920, 1920), Image.LANCZOS)  # max 1920px
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=82, optimize=True)
    buf.seek(0)

    # Upload to MinIO
    key = f'images/{uuid.uuid4()}.jpg'
    async with aioboto3.Session().client(
        's3',
        endpoint_url=settings.minio_endpoint,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
    ) as s3:
        await s3.put_object(
            Bucket='smwcs',
            Key=key,
            Body=buf.read(),
            ContentType='image/jpeg',
        )

    return {'url': f'{settings.minio_endpoint}/smwcs/{key}'}
```

---

## 6. Driver Terminal App (React Native)

### What it does
Android tablet app installed on each truck's dashboard tablet.
The driver uses it to see their route, mark stops complete, scan RFID tags,
and send emergency alerts.

### Setup

```bash
cd ~/git/SMWCS/apps/driver-terminal-app

# Install React Native CLI
npm install -g @react-native-community/cli

# Initialise React Native project (Android only)
npx react-native init SMWCSDriver --template react-native-template-typescript
cd SMWCSDriver

# Install dependencies
npm install \
  @react-navigation/native \
  @react-navigation/stack \
  react-native-screens \
  react-native-safe-area-context \
  @reduxjs/toolkit \
  react-redux \
  @react-native-async-storage/async-storage \
  react-native-camera \
  react-native-maps \
  react-native-nfc-manager
```

### Screens to build

```
LoginScreen        PIN entry + face recognition camera
HomeScreen         Map (60%) + stop list panel (40%) + load meter
StopDetailSheet    Bin address, waste type, RFID scan button, photo, notes
AlertOverlay       Full-screen modal — requires tap to dismiss — audio + vibrate
CameraView         Rear/side camera feeds, auto-activates on reverse gear
EndShiftScreen     Summary stats, signature pad, sync to server
```

### WebSocket client with offline queue

```typescript
// services/TerminalWebSocket.ts
import AsyncStorage from '@react-native-async-storage/async-storage'

const QUEUE_KEY = 'ws_offline_queue'
let ws: WebSocket | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null

export async function connect(truckId: string, token: string) {
  ws = new WebSocket(`ws://YOUR_SERVER:8005/ws/terminal/${truckId}?token=${token}`)

  ws.onopen = async () => {
    console.log('Terminal WS connected')
    await flushOfflineQueue()  // send any queued messages from offline period
  }

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data)
    handleIncoming(msg)
  }

  ws.onclose = () => {
    console.log('Terminal WS disconnected — reconnecting in 3s')
    reconnectTimer = setTimeout(() => connect(truckId, token), 3000)
  }
}

export async function sendMessage(msg: object) {
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(msg))
  } else {
    // Queue for when connection restores
    const queue = JSON.parse(await AsyncStorage.getItem(QUEUE_KEY) || '[]')
    queue.push(msg)
    await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(queue))
  }
}

async function flushOfflineQueue() {
  const queue = JSON.parse(await AsyncStorage.getItem(QUEUE_KEY) || '[]')
  for (const msg of queue) {
    ws?.send(JSON.stringify(msg))
  }
  await AsyncStorage.removeItem(QUEUE_KEY)
}
```

---

## 7. Citizen App (React Native)

### What it does
Mobile app for Nairobi citizens to check collection schedules, report overflowing
bins, see live truck location, and request special pickups.

### Setup

```bash
cd ~/git/SMWCS/apps/citizen-app

npx react-native init SMWCSCitizen --template react-native-template-typescript
cd SMWCSCitizen

npm install \
  @react-navigation/native \
  @react-navigation/bottom-tabs \
  react-native-maps \
  react-native-camera \
  react-native-geolocation-service \
  @notifee/react-native \
  @react-native-firebase/app \
  @react-native-firebase/messaging \
  axios
```

### Screens to build

```
HomeScreen           Next pickup countdown + collection schedule card + recycling score
ScheduleScreen       Monthly calendar view + sync to phone calendar
TruckTrackerScreen   Live map showing nearest truck in zone + ETA countdown
SortingCameraScreen  Point camera at waste → on-device TFLite classifier shows result
ReportBinScreen      Camera capture + GPS pin on map + description form + submit
SpecialPickupScreen  Item type selector + photo upload + date picker + submit
ProfileScreen        Name, address, zone, notification preferences
```

### Push notifications (FCM)

```typescript
// notifications.ts
import messaging from '@react-native-firebase/messaging'

export async function setupPushNotifications() {
  await messaging().requestPermission()
  const token = await messaging().getToken()
  // Register token with citizen-api for server-side pushes
  await api.registerFCMToken(token)
}

// Server sends push for:
// - 'collection_tomorrow' — day before scheduled collection
// - 'truck_nearby'        — truck is < 500m from address
// - 'report_acknowledged' — council acknowledged your bin report
```

---

## Testing the Full Pipeline (after all services built)

```bash
# 1. Send a critical bin fill via MQTT
mosquitto_pub -h localhost -p 1883 \
  -t "smwcs/sensors/SN-NBI-001/telemetry" \
  -m '{"fill_pct":93,"temp_c":27,"battery_pct":80,"rssi":-65,"waste_type":"burnable","zone_id":"bc2437c2-...","lat":-1.2692,"lon":36.8090}'

# Expected cascade:
# iot-ingestion  → writes to InfluxDB
#                → publishes bin.sensor.reading
#                → publishes bin.fill.critical (fill≥90)
#
# alert-service  → consumes bin.fill.critical
#                → creates alert (bin_overflow, critical) in PostgreSQL
#                → publishes alert.created
#
# route-engine   → consumes bin.fill.critical
#                → forces immediate re-optimisation for zone
#                → solves CVRP with OSRM distances
#                → publishes route.updated for affected truck
#
# driver-terminal→ consumes route.updated
#                → pushes ROUTE_DELTA to truck's WebSocket
#                → driver tablet shows new stop
#
# command-api    → consumes alert.created + route.updated
#                → broadcasts to all dashboard WebSocket clients
#                → dashboard shows new alert + updated route progress
```
