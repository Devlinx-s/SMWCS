# CHANGELOG
## SMWCS — Smart Municipal Waste Collection System

All notable changes to this project are documented here.
Format: `[version] — date — description`

---

## [0.3.0] — 2026-03-22 — Command Dashboard Live

### Added
- **React command dashboard** (`apps/dashboard/`) — full command center UI
  - Login page with JWT auth stored in localStorage
  - Dashboard page: stat cards (trucks on route, available, open alerts, active bins, drivers, high alerts), active fleet table with load progress bars, live alert feed with ACK button
  - Fleet page: truck table (registration, make/model, status badge, capacity, load, fuel), driver roster table
  - Bins page: bin registry table with zone name lookup, status badges, sensor assignment
  - Alerts page: severity stat cards, filter (open/all/resolved), full alert table with ACK and Resolve actions
  - Drivers page: driver roster and shift history table
  - Sidebar: live WS connection indicator, user profile, sign out
  - Dark theme with Nairobi-appropriate colour scheme (teal accent)
- **Zustand stores**: `useAuthStore` (token, user, login/logout), `useWsStore` (WS state, live truck positions, live alerts)
- **TanStack Query** for all REST data with auto-refetch intervals (10–30s)
- **Vite proxy** configuration for all 4 backend services
- **WebSocket client** in `api.js` with auto-reconnect (3s backoff) and 30s ping keepalive

### Fixed
- `QueryClientProvider` missing from `main.jsx` after Vite scaffold overwrote it
- Fleet and Bins pages stuck loading due to CORS — fixed with Vite proxy
- WebSocket `setConnected` not called on connect/disconnect — passed callbacks to `createDashboardWS`

---

## [0.2.5] — 2026-03-22 — Command API

### Added
- **command-api service** (`services/command-api/`) on port 8007
  - `GET /api/v1/fleet/live` — trucks joined with active shift and driver via raw SQL
  - `GET /api/v1/fleet/stats` — count by status (available, on_route, maintenance, offline)
  - `GET /api/v1/alerts/` — list with filters (resolved, severity, zone_id, limit)
  - `POST /api/v1/alerts/{id}/acknowledge` — sets acknowledged=true + acknowledged_by + acknowledged_at
  - `POST /api/v1/alerts/{id}/resolve` — sets resolved=true + resolved_at
  - `GET /api/v1/alerts/stats` — count by severity + resolved count
  - `GET /api/v1/analytics/summary` — trucks, bins, alerts, drivers summary
  - `WS /ws/dashboard` — WebSocket endpoint, accepts `ping` → replies `pong`
- **DashboardBroadcaster** — WebSocket connection manager, broadcasts to all connected clients
- **Kafka fanout worker** — background asyncio task consuming truck.position, alert.created, bin.fill.critical, route.updated → WebSocket broadcast

---

## [0.2.4] — 2026-03-22 — Alert Service

### Added
- **alert-service** (`services/alert-service/`) — background Kafka consumer
  - `Alert` SQLAlchemy model with JSONB `alert_metadata` field
  - Threshold rules engine in `app/rules.py`
  - Kafka consumer on `bin.sensor.reading`, `bin.fill.critical`, `truck.telemetry`
  - Writes alerts to PostgreSQL `alerts` table
  - Publishes `alert.created` to Kafka for downstream consumers
  - Alert types: bin_overflow, bin_fire, sensor_low_battery, truck_overload (+ 7 others defined)
  - Severity levels: low, medium, high, critical

### Fixed
- `metadata` column name reserved by SQLAlchemy DeclarativeBase — renamed to `alert_metadata`
- `truck.telemetry` Kafka topic did not exist — created with 3 partitions

---

## [0.2.3] — 2026-03-22 — IoT Ingestion

### Added
- **iot-ingestion service** (`services/iot-ingestion/`) — MQTT subscriber
  - `aiomqtt` async subscriber with auto-reconnect (5s backoff)
  - Pydantic schemas: `SensorTelemetry`, `TruckPosition`, `SensorAlert`
  - InfluxDB writer: `write_sensor_reading()` and `write_truck_position()`
  - Kafka publisher using confluent-kafka
  - Handler routing: `smwcs/sensors/+/telemetry` → `handle_sensor_telemetry()`, `smwcs/trucks/+/position` → `handle_truck_position()`
  - Critical fill detection: fill_pct ≥ 90 publishes additional `bin.fill.critical` event
  - Fire detection: temp_c ≥ 60 publishes `bin.alert` with type `bin_fire`
- All 9 Kafka topics created with 3 partitions each
- `fleet_positions` InfluxDB bucket created (30-day retention)

### Fixed
- System Mosquitto service disabled (`sudo systemctl disable mosquitto`) — was blocking port 1883
- `sensor_telemetry` bucket already existed from InfluxDB init, `fleet_positions` was missing

---

## [0.2.2] — 2026-03-22 — Fleet Service

### Added
- **fleet-service** (`services/fleet-service/`) on port 8003
  - `Truck` model: registration, make, model, year, capacity_kg, capacity_litres, fuel_type, gps_unit_id, terminal_device_id, status, current_location (PostGIS POINT), current_load_kg, odometer_km
  - `Driver` model: employee_id, first_name, last_name, phone, email, license_number, license_expiry, status
  - `Shift` model: truck_id, driver_id, planned_start/end, actual_start/end, status
  - Truck CRUD: GET list (filter by status), POST create, GET by id, PATCH update, DELETE decommission
  - Driver CRUD: GET list (filter by status), POST create, GET by id, PATCH update
  - Shift endpoints: GET list, GET active, POST create, POST start (→ truck on_route), POST end (→ truck available)
  - Shift lifecycle enforced: can only start scheduled shifts, can only end active shifts
- Pilot data loaded:
  - 3 trucks: KBZ 001A, KBZ 002B, KBZ 003C (Isuzu NPR 2022, 3000kg capacity)
  - 3 drivers: James Mwangi (DRV-001), Peter Kamau (DRV-002), Grace Wanjiku (DRV-003)
  - 1 shift: KBZ 001A + James Mwangi, started → truck status = on_route

---

## [0.2.1] — 2026-03-22 — Bin Registry

### Added
- **bin-registry service** (`services/bin-registry/`) on port 8002
  - `Zone` model with PostGIS POLYGON boundary (SRID 4326)
  - `Bin` model with PostGIS POINT location (SRID 4326)
  - `Sensor` model for hardware registry
  - Zone CRUD: list, create (with GeoJSON boundary → WKT), get by id
  - Bin CRUD: list (filter: zone_id, status, pagination), create (with lat/lon → ST_MakePoint), get, update, soft-delete (→ decommissioned)
  - Zone fill summary endpoint (count by fill tier)
- Pilot data loaded:
  - Zone: Westlands Zone A (NBI-WEST-A), district Westlands, population 45,000
  - 5 bins: BIN-NBI-001 to BIN-NBI-005, 240L capacity, Westlands Road

---

## [0.2.0] — 2026-03-22 — Auth Service

### Added
- **auth-service** (`services/auth-service/`) on port 8001 — first service running
  - FastAPI app with asynccontextmanager lifespan
  - SQLAlchemy 2.0 async engine with asyncpg driver
  - `SystemUser` model: UUID primary key, email, bcrypt password hash, role enum (6 roles), MFA fields, audit timestamps
  - JWT access tokens (15 min) + UUID4 refresh tokens (7 days, stored in Redis)
  - RBAC: `has_permission()` with resource:action format, `require_permission()` FastAPI dependency factory
  - TOTP MFA: pyotp + qrcode for setup, verify endpoint to enable
  - Endpoints: login, refresh, logout, me, mfa/setup, mfa/verify, change-password, users CRUD
  - Auto-creates tables via `Base.metadata.create_all` on startup (dev mode)
- Pilot user created: `admin@smwcs.co.ke` / `Admin1234!` / role: super_admin

### Fixed
- `email-validator` package missing — installed `pydantic[email]`
- `bcrypt` incompatibility with passlib on newer versions — pinned to `bcrypt==4.0.1`
- `poetry shell` not available in Poetry 2.0 — using `eval $(poetry env activate)` instead
- PostgreSQL `smwcs` user password mismatch — recreated volume with correct credentials
- System PostgreSQL on port 5432 blocking Docker — `sudo systemctl stop postgresql && sudo systemctl disable postgresql`
- System Redis on port 6379 blocking Docker — `sudo systemctl stop redis-server && sudo systemctl disable redis-server`
- Docker Redis container started without port binding (stale container) — force-recreated with `docker compose up -d --force-recreate redis`

---

## [0.1.0] — 2026-03-22 — Infrastructure Bootstrap

### Added
- Monorepo directory structure created:
  ```
  services/{auth-service,bin-registry,fleet-service,iot-ingestion,
            route-engine,driver-terminal,alert-service,command-api,
            citizen-api,analytics-service,media-service}
  apps/{dashboard,driver-terminal-app,citizen-app}
  infrastructure/{docker,scripts}
  docs/
  ```
- `docker-compose.yml` with all 8 backing services
- `infrastructure/docker/mosquitto.conf` — anonymous MQTT (dev mode)
- `.env.example` — all environment variable templates
- `.gitignore` — Python, Node, Docker, secrets exclusions

### Infrastructure fixes
- `version:` field removed from docker-compose.yml (deprecated in newer Docker Compose)
- `x-common-env` anchor syntax caused validation error — replaced with explicit per-service env blocks
- System Mosquitto on port 1883 — disabled system service
- System PostgreSQL on port 5432 — disabled system service
- System Redis on port 6379 — disabled system service

### Dev environment
- Ubuntu 22.04 on developer machine
- Python 3.11.9 via pyenv
- Poetry 2.0+ for dependency management
- Docker Engine + Docker Compose v2 plugin
- Node.js 18 via nvm
- VS Code with Python, Ruff, Docker, GitLens extensions

---

## Upcoming — [0.4.0] — Route Engine

### Planned
- Download Kenya OSM map data from geofabrik.de
- Run OSRM pre-processing (extract, partition, customize)
- Build `ZoneStateManager` — in-memory state of bin fills and truck positions
- Build `build_distance_matrix()` — calls OSRM Table API
- Build `solve_cvrp()` — OR-Tools RoutingModel with capacity constraints
- Kafka consumer on `bin.sensor.reading` and `bin.fill.critical`
- 5-minute re-optimisation interval per zone
- Immediate re-optimisation on `bin.fill.critical` events
- Publish `route.updated` to Kafka

### Planned — [0.5.0] — Driver Terminal
- WebSocket server with terminal auth handshake
- ROUTE_FULL push on WS connection
- ROUTE_DELTA push on route.updated
- STOP_COMPLETED PostgreSQL write
- DRIVER_EMERGENCY alert creation

### Planned — [0.6.0] — Citizen API + Analytics
- Citizen REST API (MongoDB-backed)
- Collection schedule endpoint
- Bin report with Kafka publish
- Truck ETA endpoint
- Celery analytics tasks
