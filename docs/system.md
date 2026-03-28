# System Documentation
## SMWCS — Smart Municipal Waste Collection System

---

## 1. Technology Stack

### Backend
| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Language | Python | 3.11 | All backend services |
| Web framework | FastAPI | 0.111+ | REST APIs and WebSocket |
| ASGI server | Uvicorn | 0.29+ | Production HTTP server |
| ORM | SQLAlchemy | 2.0 (async) | PostgreSQL access |
| Migrations | Alembic | 1.13+ | Schema versioning |
| Validation | Pydantic v2 | 2.7+ | Request/response schemas |
| Config | pydantic-settings | 2.2+ | .env parsing |
| Auth tokens | python-jose | 3.3+ | JWT encode/decode |
| Passwords | passlib + bcrypt 4.0.1 | — | Password hashing |
| MFA | pyotp | 2.9+ | TOTP codes |
| QR codes | qrcode | 7.4+ | MFA setup QR |
| Geospatial | geoalchemy2 + shapely | — | PostGIS integration |
| Time-series | influxdb-client | async | InfluxDB writes |
| Messaging | confluent-kafka | 2.13+ | Kafka producer/consumer |
| MQTT | aiomqtt | — | MQTT subscriber |
| Cache | redis[hiredis] | 5.0+ | Token storage |
| HTTP client | httpx | 0.27+ | Inter-service calls |
| Logging | structlog | 24.1+ | Structured JSON logs |
| Metrics | prometheus-client | 0.20+ | /metrics endpoint |
| Dependency mgmt | Poetry | 2.0+ | Per-service venvs |

### Databases & Messaging
| Service | Version | Port | Purpose |
|---|---|---|---|
| PostgreSQL + PostGIS | 16 + 3.4 | 5432 | Primary relational store |
| InfluxDB | 2.7 | 8086 | Sensor + GPS time-series |
| Redis | 7 | 6379 | JWT tokens, caching |
| MongoDB | 7 | 27018 | Citizen data |
| Apache Kafka | 7.6 (Confluent) | 9092 | Event streaming |
| Zookeeper | 7.6 (Confluent) | 2181 | Kafka coordination |
| Eclipse Mosquitto | 2 | 1883 | MQTT broker |
| MinIO | latest | 9000/9001 | Object storage |

### Frontend
| Technology | Version | Purpose |
|---|---|---|
| React | 18.2 | Dashboard UI framework |
| Vite | 8.0 | Build tool and dev server |
| Axios | latest | HTTP API calls |
| React Router | 6 | Client-side routing |
| TanStack Query | 5 | Server state management |
| Zustand | latest | Client state (auth, WS) |
| Recharts | latest | Analytics charts |
| Leaflet + React-Leaflet | 1.9.4 | Maps |
| React Hot Toast | latest | Notifications |

---

## 2. Service Specifications

### 2.1 Auth Service (port 8001)

**Purpose:** Central authentication and authorisation for all SMWCS services.

**Endpoints:**

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /api/v1/auth/login | None | Email + password login, returns JWT pair |
| POST | /api/v1/auth/refresh | None | Exchange refresh token for new access token |
| POST | /api/v1/auth/logout | None | Invalidate refresh token in Redis |
| GET | /api/v1/auth/me | Bearer | Get current user profile |
| POST | /api/v1/auth/mfa/setup | Bearer | Generate TOTP secret and QR code |
| POST | /api/v1/auth/mfa/verify | Bearer | Confirm TOTP code and enable MFA |
| POST | /api/v1/auth/change-password | Bearer | Change own password |
| GET | /api/v1/users/ | Bearer + users:read | List all system users |
| POST | /api/v1/users/ | Bearer + users:read | Create new system user |
| PATCH | /api/v1/users/{id}/deactivate | Bearer + users:read | Deactivate a user |

**Token design:**
- Access token: JWT, 15-minute expiry, signed with HS256
- Refresh token: UUID4, 7-day expiry, stored in Redis as `refresh:<uuid> → user_id`
- Claims: `sub` (user_id), `role`, `email`, `iss` (smwcs-auth), `aud` (smwcs-api)

**Database table:** `system_users`
```sql
id            UUID PRIMARY KEY
email         VARCHAR(150) UNIQUE NOT NULL
password_hash VARCHAR(256) NOT NULL
first_name    VARCHAR(80) NOT NULL
last_name     VARCHAR(80) NOT NULL
role          userrole ENUM NOT NULL
is_active     BOOLEAN DEFAULT true
mfa_secret    VARCHAR(100)
mfa_enabled   BOOLEAN DEFAULT false
last_login    TIMESTAMPTZ
created_at    TIMESTAMPTZ DEFAULT now()
updated_at    TIMESTAMPTZ DEFAULT now()
```

---

### 2.2 Bin Registry (port 8002)

**Purpose:** Master registry of all zones, bins, and sensors.

**Endpoints:**

| Method | Path | Permission | Description |
|---|---|---|---|
| GET | /api/v1/zones/ | bins:read | List all zones |
| POST | /api/v1/zones/ | zones:write | Create zone with PostGIS polygon |
| GET | /api/v1/zones/{id} | bins:read | Get zone by ID |
| GET | /api/v1/bins/ | bins:read | List bins (filter: zone_id, status, page) |
| POST | /api/v1/bins/ | bins:write | Register new bin |
| GET | /api/v1/bins/{id} | bins:read | Get bin by ID |
| PATCH | /api/v1/bins/{id} | bins:write | Update bin (status, sensor, address) |
| DELETE | /api/v1/bins/{id} | bins:write | Decommission bin |
| GET | /api/v1/bins/zone/{id}/summary | bins:read | Fill level summary for a zone |

**Database tables:**
```sql
-- zones
id         UUID PRIMARY KEY
name       VARCHAR(100) NOT NULL
code       VARCHAR(20) UNIQUE NOT NULL
boundary   GEOMETRY(POLYGON, 4326) NOT NULL
district   VARCHAR(100)
population INTEGER
created_at TIMESTAMPTZ DEFAULT now()
updated_at TIMESTAMPTZ DEFAULT now()

-- bins
id              UUID PRIMARY KEY
zone_id         UUID (FK zones.id)
sensor_id       VARCHAR(64) UNIQUE
serial_number   VARCHAR(64) UNIQUE NOT NULL
location        GEOMETRY(POINT, 4326) NOT NULL
address         TEXT
capacity_litres INTEGER DEFAULT 120
status          binstatus ENUM (active/maintenance/decommissioned/pending_install)
install_date    DATE
last_serviced   TIMESTAMPTZ
notes           TEXT
created_at      TIMESTAMPTZ DEFAULT now()
updated_at      TIMESTAMPTZ DEFAULT now()

-- sensors
id               UUID PRIMARY KEY
hardware_id      VARCHAR(64) UNIQUE NOT NULL
firmware_version VARCHAR(20)
sim_iccid        VARCHAR(30)
install_date     DATE
last_seen        TIMESTAMPTZ
battery_pct      INTEGER
rssi             INTEGER
is_online        BOOLEAN DEFAULT true
created_at       TIMESTAMPTZ DEFAULT now()
```

---

### 2.3 Fleet Service (port 8003)

**Purpose:** Truck, driver, and shift management including lifecycle transitions.

**Endpoints:**

| Method | Path | Permission | Description |
|---|---|---|---|
| GET | /api/v1/trucks/ | trucks:read | List trucks (filter: status) |
| POST | /api/v1/trucks/ | trucks:write | Register truck |
| GET | /api/v1/trucks/{id} | trucks:read | Get truck |
| PATCH | /api/v1/trucks/{id} | trucks:write | Update truck |
| DELETE | /api/v1/trucks/{id} | trucks:write | Set truck offline |
| GET | /api/v1/drivers/ | drivers:read | List drivers (filter: status) |
| POST | /api/v1/drivers/ | drivers:write | Register driver |
| GET | /api/v1/drivers/{id} | drivers:read | Get driver |
| PATCH | /api/v1/drivers/{id} | drivers:write | Update driver |
| GET | /api/v1/shifts/ | shifts:read | List shifts (last 100) |
| GET | /api/v1/shifts/active | shifts:read | List all active shifts |
| POST | /api/v1/shifts/ | shifts:write | Create shift (scheduled) |
| POST | /api/v1/shifts/{id}/start | shifts:write | Start shift → truck goes on_route |
| POST | /api/v1/shifts/{id}/end | shifts:write | End shift → truck goes available |

**Shift lifecycle:**
```
scheduled → active (start) → completed (end)
                           → cancelled
```

**Database tables:** `trucks`, `drivers`, `shifts` (see models/fleet.py)

---

### 2.4 IoT Ingestion Service (no HTTP port)

**Purpose:** Subscribe to all MQTT topics, validate payloads, write to InfluxDB, publish to Kafka.

**MQTT subscriptions:**
```
smwcs/sensors/+/telemetry
smwcs/sensors/+/alert
smwcs/trucks/+/position
smwcs/trucks/+/telemetry
smwcs/trucks/+/rfid
```

**Processing pipeline per message:**
1. Parse topic → extract entity_type, entity_id, message_type
2. Validate JSON payload against Pydantic schema
3. Write to InfluxDB (sensor_telemetry or fleet_positions bucket)
4. Publish to Kafka topic
5. Check critical thresholds → publish additional alert events if triggered

**Kafka publishes:**

| Trigger | Topic |
|---|---|
| Any sensor reading | `bin.sensor.reading` |
| fill_pct ≥ 90 | `bin.fill.critical` (additional) |
| temp_c ≥ 60 | `bin.alert` (fire alert) |
| Any truck position | `truck.position` |

**InfluxDB measurements:**
```
bin_reading
  tags:   sensor_id, zone_id, waste_type
  fields: fill_pct, weight_kg, temp_c, battery_pct, rssi

truck_position
  tags:   truck_id
  fields: lat, lon, speed_kmh, heading, load_kg, fuel_pct
```

---

### 2.5 Alert Service (no HTTP port)

**Purpose:** Consume Kafka events, evaluate threshold rules, write alerts to PostgreSQL.

**Kafka subscriptions:**
```
bin.sensor.reading
bin.fill.critical
truck.telemetry
```

**Alert rules engine (app/rules.py):**

| Rule | Alert Type | Severity |
|---|---|---|
| fill_pct ≥ 95 | bin_overflow | critical |
| fill_pct ≥ 80 | bin_overflow | high |
| temp_c ≥ 60 | bin_fire | critical |
| battery_pct < 15 | sensor_low_battery | low |
| load_kg > capacity × 0.95 | truck_overload | high |

**Database table:** `alerts`
```sql
id               UUID PRIMARY KEY
type             alerttype ENUM
severity         alertseverity ENUM
sensor_id        VARCHAR(64)
truck_id         VARCHAR(64)
zone_id          VARCHAR(64)
message          TEXT NOT NULL
alert_metadata   JSONB
acknowledged     BOOLEAN DEFAULT false
acknowledged_by  VARCHAR(64)
acknowledged_at  TIMESTAMPTZ
resolved         BOOLEAN DEFAULT false
resolved_at      TIMESTAMPTZ
resolution_notes TEXT
created_at       TIMESTAMPTZ DEFAULT now()
```

**Kafka publishes:** `alert.created` for every alert written

---

### 2.6 Command API (port 8007)

**Purpose:** Unified REST and WebSocket API for the React command dashboard.

**REST Endpoints:**

| Method | Path | Permission | Description |
|---|---|---|---|
| GET | /api/v1/fleet/live | trucks:read | All trucks with driver, shift, load data |
| GET | /api/v1/fleet/stats | trucks:read | Count by status |
| GET | /api/v1/alerts/ | alerts:read | List alerts with filters |
| POST | /api/v1/alerts/{id}/acknowledge | alerts:write | Acknowledge alert |
| POST | /api/v1/alerts/{id}/resolve | alerts:write | Resolve alert |
| GET | /api/v1/alerts/stats | alerts:read | Count by severity |
| GET | /api/v1/analytics/summary | analytics:read | System-wide summary |

**WebSocket:**
```
ws://localhost:8007/ws/dashboard
```

Client sends `ping` every 30s. Server replies `pong`.
Server pushes JSON frames from Kafka:
```json
{"type": "TRUCK_POSITION", "data": {...}}
{"type": "ALERT_CREATED",  "data": {...}}
{"type": "BIN_FILL_CRITICAL", "data": {...}}
{"type": "ROUTE_UPDATED",  "data": {...}}
```

**Kafka fanout worker:**
Runs as a background asyncio task. Consumes:
- `truck.position` → broadcast `TRUCK_POSITION`
- `alert.created` → broadcast `ALERT_CREATED`
- `bin.fill.critical` → broadcast `BIN_FILL_CRITICAL`
- `bin.sensor.reading` → broadcast `BIN_SENSOR_READING`
- `route.updated` → broadcast `ROUTE_UPDATED`

---

### 2.7 React Dashboard (port 5173)

**Pages:**

| Page | Route key | Data sources |
|---|---|---|
| Dashboard | `dashboard` | command-api: summary, fleet/live, fleet/stats, alerts/stats, alerts |
| Fleet | `fleet` | fleet-service: trucks, drivers |
| Bins | `bins` | bin-registry: bins, zones |
| Alerts | `alerts` | command-api: alerts (with filters), alerts/stats |
| Drivers | `drivers` | fleet-service: drivers, shifts |

**State management:**
- `useAuthStore` (Zustand): JWT token, user profile, login/logout
- `useWsStore` (Zustand): WS connection status, live truck positions, live alerts
- TanStack Query: all REST data with 10–30 second refetch intervals

**API proxy (Vite dev):**
```
/auth/*    → http://localhost:8001
/bins/*    → http://localhost:8002
/fleet/*   → http://localhost:8003
/command/* → http://localhost:8007
```

---

## 3. Infrastructure

### Docker Compose Services
All backing services run in Docker. Application services run locally during development.

```yaml
postgres:    postgis/postgis:16-3.4   port 5432
influxdb:    influxdb:2.7             port 8086
redis:       redis:7-alpine            port 6379
mongo:       mongo:7                   port 27018
zookeeper:   cp-zookeeper:7.6.0       internal
kafka:       cp-kafka:7.6.0           port 9092
mosquitto:   eclipse-mosquitto:2      port 1883
minio:       minio/minio:latest       port 9000/9001
```

### Kafka Topics Created
```bash
bin.sensor.reading    partitions: 3
bin.fill.critical     partitions: 3
bin.alert             partitions: 3
truck.position        partitions: 3
truck.telemetry       partitions: 3
route.updated         partitions: 3
stop.completed        partitions: 3
alert.created         partitions: 3
alert.driver          partitions: 3
```

### InfluxDB Buckets
```
sensor_telemetry    retention: 90 days
fleet_positions     retention: 30 days
```

### MQTT Config
```
listener 1883
allow_anonymous true    (dev only — password file required in production)
```

---

## 4. Security

### JWT Token Flow
```
Client          Auth Service         Redis
  │─── POST /login ────────────────▶ │
  │                                  │─── HSET refresh:<uuid> = user_id ──▶ │
  │◀── {access_token, refresh_token} │
  │─── GET /api/* (Bearer token) ──▶ Any service (validates JWT locally)
  │─── POST /refresh ───────────────▶ Auth Service
  │                                  │─── GET refresh:<uuid> ──────────────▶ │
  │◀── {access_token} ───────────────│
```

### Token Storage (browser)
- Access token: `localStorage.smwcs_token`
- Refresh: not stored in browser — re-login required when access token expires

### Password Security
- bcrypt with cost factor 12
- Library: passlib[bcrypt] pinned to bcrypt==4.0.1 (compatibility fix)

### RBAC Enforcement
Every FastAPI dependency calls `has_permission(role, required_permission)`.
The permission string format is `resource:action` e.g. `bins:read`, `trucks:write`.
`super_admin` role has `*` which bypasses all checks.

---

## 5. Development Workflow

### Starting for development (daily)

```bash
# Terminal 1 — backing services
cd ~/git/SMWCS
docker compose up -d postgres influxdb redis mongo kafka zookeeper mosquitto minio

# Terminal 2 — auth service
cd ~/git/SMWCS/services/auth-service
eval $(poetry env activate)
poetry run uvicorn app.main:app --reload --port 8001

# Terminal 3 — bin registry
cd ~/git/SMWCS/services/bin-registry
eval $(poetry env activate)
poetry run uvicorn app.main:app --reload --port 8002

# Terminal 4 — fleet service
cd ~/git/SMWCS/services/fleet-service
eval $(poetry env activate)
poetry run uvicorn app.main:app --reload --port 8003

# Terminal 5 — IoT ingestion
cd ~/git/SMWCS/services/iot-ingestion
eval $(poetry env activate)
poetry run python -m app.main

# Terminal 6 — alert service
cd ~/git/SMWCS/services/alert-service
eval $(poetry env activate)
poetry run python -m app.main

# Terminal 7 — command API
cd ~/git/SMWCS/services/command-api
eval $(poetry env activate)
poetry run uvicorn app.main:app --reload --port 8007

# Terminal 8 — dashboard
cd ~/git/SMWCS/apps/dashboard
npm run dev
```

### Testing a sensor reading end-to-end

```bash
# Send a bin sensor reading via MQTT
mosquitto_pub -h localhost -p 1883 \
  -t "smwcs/sensors/SN-TEST-001/telemetry" \
  -m '{
    "fill_pct": 88.0,
    "weight_kg": 48.0,
    "temp_c": 27.0,
    "battery_pct": 12,
    "rssi": -72,
    "waste_type": "burnable",
    "zone_id": "bc2437c2-eafc-4526-a138-8f9ad2f4ed37"
  }'

# Expected results:
# iot-ingestion:  sensor.written (InfluxDB) + kafka publish
# alert-service:  alert.created (bin_overflow high + sensor_low_battery low)
# command-api WS: broadcasts ALERT_CREATED to dashboard clients
# dashboard:      alert appears in Live Alerts feed
```

### API testing credentials

```
Email:    admin@smwcs.co.ke
Password: Admin1234!
Role:     super_admin
```

Get a token:
```bash
TOKEN=$(curl -s -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@smwcs.co.ke", "password": "Admin1234!"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

---

## 6. What Is NOT Yet Built

### route-engine (port 8004)
- OR-Tools CVRP solver
- OSRM distance matrix builder
- ZoneStateManager (in-memory bin fill + truck positions)
- Kafka consumer (bin.sensor.reading, bin.fill.critical)
- Kafka publisher (route.updated)
- Kenya OSM data download and OSRM pre-processing required first

### driver-terminal (port 8005)
- WebSocket server for Android tablets
- AUTH handshake with terminal token
- ROUTE_FULL push on connect
- ROUTE_DELTA push on route.updated
- STOP_COMPLETED handler
- DRIVER_EMERGENCY alert trigger

### citizen-api (port 8008)
- Citizen registration + JWT
- Collection schedule endpoint
- Bin problem report
- Truck ETA endpoint
- Special pickup request
- TensorFlow waste classification endpoint

### analytics-service
- Celery + Redis broker setup
- Hourly zone aggregation task
- Daily driver KPI computation
- Weekly zone report task

### media-service (port 8012)
- MinIO/S3 async upload
- Pillow image compression
- CDN URL generation

### apps/driver-terminal-app
- React Native Android app
- WebSocket client with offline queue
- MapLibre route display
- RFID scan handler
- AlertOverlay component

### apps/citizen-app
- React Native iOS/Android
- Collection schedule display
- Live truck tracker map
- Bin report camera flow
- FCM push notifications
