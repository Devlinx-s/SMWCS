# AGENTS.md
## AI Agent Instructions for SMWCS Codebase

This file tells any AI coding agent (Claude, Cursor, Copilot, etc.) how to work
safely and consistently inside the SMWCS monorepo.

---

## Project Identity

**Name:** Smart Municipal Waste Collection System (SMWCS)  
**Deployment:** Nairobi, Kenya  
**Stack:** Python 3.11 / FastAPI / PostgreSQL+PostGIS / InfluxDB / Redis / Kafka / MQTT / React 18 / Vite  
**Repo layout:** Monorepo — one Git repository, many independent services  

---

## Monorepo Structure

```
SMWCS/
  services/
    auth-service/          ← JWT auth, RBAC, MFA          port 8001
    bin-registry/          ← Zones, bins, sensors          port 8002
    fleet-service/         ← Trucks, drivers, shifts       port 8003
    iot-ingestion/         ← MQTT subscriber               no HTTP port
    alert-service/         ← Kafka consumer, PG writes     no HTTP port
    command-api/           ← REST + WebSocket dashboard    port 8007
    route-engine/          ← OR-Tools CVRP solver          port 8004  (TODO)
    driver-terminal/       ← WS server for tablets         port 8005  (TODO)
    citizen-api/           ← Citizen REST API              port 8008  (TODO)
    analytics-service/     ← Celery background jobs        no HTTP    (TODO)
    media-service/         ← MinIO / S3 uploads            port 8012  (TODO)
  apps/
    dashboard/             ← React 18 + Vite command center  port 5173
    driver-terminal-app/   ← React Native Android app       (TODO)
    citizen-app/           ← React Native citizen app       (TODO)
  infrastructure/
    docker/                ← mosquitto.conf, Dockerfiles
    scripts/               ← utility scripts
  docs/                    ← all documentation lives here
  docker-compose.yml       ← all backing services
  .env.example             ← environment variable template
```

---

## Rules Every Agent Must Follow

### 1. Never touch the wrong service's files
Each service is an independent Python package with its own `pyproject.toml`,
`.env`, and `alembic/` folder. Do not import across service boundaries.
If two services need to share logic, use Kafka messages — not shared imports.

### 2. Always use async SQLAlchemy
All database calls use `async with AsyncSessionLocal() as session`.
Never use synchronous `session.execute()` in a FastAPI route.
Never use `session.commit()` outside of the `get_db()` dependency.

### 3. RBAC is enforced on every endpoint
Every FastAPI route that returns data must include a `require_permission()` dependency.
Never expose an unauthenticated endpoint except `/health` and `/docs`.
Permissions reference: see `PERMISSIONS` dict in each service's `app/core/deps.py`.

### 4. Kafka topics are the integration layer
Services communicate via Kafka only — never via direct HTTP calls to each other.
Kafka topics in use:

| Topic | Publisher | Consumers |
|---|---|---|
| `bin.sensor.reading` | iot-ingestion | alert-service, route-engine |
| `bin.fill.critical` | iot-ingestion | alert-service, route-engine |
| `bin.alert` | iot-ingestion | alert-service |
| `truck.position` | iot-ingestion | command-api (fanout) |
| `truck.telemetry` | iot-ingestion | alert-service |
| `alert.created` | alert-service | command-api (fanout) |
| `alert.driver` | alert-service | driver-terminal |
| `route.updated` | route-engine | driver-terminal, command-api |
| `stop.completed` | driver-terminal | route-engine, analytics-service |

### 5. Environment variables only — no hardcoded config
All config comes from `.env` via `pydantic_settings.BaseSettings`.
Never hardcode passwords, tokens, hostnames, or port numbers in source code.
Always read from `get_settings()`.

### 6. PostGIS for all geospatial data
Bin locations and zone boundaries are stored as PostGIS geometry types.
Always use `geoalchemy2` for spatial columns.
Always use SRID 4326 (WGS84 — standard GPS coordinates).
Nairobi coordinates: approximately lat -1.286, lon 36.817.

### 7. InfluxDB for time-series only
Only two things go in InfluxDB:
- `sensor_telemetry` bucket: bin sensor readings (fill %, temperature, battery)
- `fleet_positions` bucket: truck GPS positions

Everything else (alerts, users, bins, routes) goes in PostgreSQL.

### 8. Structlog for all logging
Never use `print()` or `logging.basicConfig()`.
Always use `structlog.get_logger()` and structured key=value pairs.

```python
log = structlog.get_logger()
log.info('event.name', key1=value1, key2=value2)
log.warning('threshold.exceeded', sensor_id=sid, fill_pct=fill)
log.error('connection.failed', service='influxdb', error=str(e))
```

### 9. Alembic for all schema changes
Never use `Base.metadata.create_all()` in production (only in dev lifespan).
All schema changes must have an Alembic migration file.
Run migrations before starting a service: `alembic upgrade head`.

### 10. Testing conventions
- Test files: `tests/test_*.py`
- Use `pytest` with `pytest-asyncio`
- Use `Testcontainers` for integration tests (real PostgreSQL, real Redis)
- Minimum coverage: 75% per service before merging

---

## Adding a New Service

1. `cd services/<service-name>`
2. `poetry init --name <service-name> --python "^3.11" --no-interaction`
3. Copy `app/config.py`, `app/database.py`, `app/core/deps.py` from an existing service
4. Create `app/main.py` with FastAPI app + lifespan + CORS + `/health`
5. Create `.env` from `.env.example`
6. Add service to `docker-compose.yml`
7. Update `docs/project_context.md` service table
8. Update `CHANGELOG.md`

---

## Common Commands

```bash
# Start all backing services
docker compose up -d postgres influxdb redis mongo kafka zookeeper mosquitto minio

# Run a service locally
cd services/<name>
poetry run uvicorn app.main:app --reload --port <port>

# Run background service (no HTTP)
poetry run python -m app.main

# Send test MQTT message
mosquitto_pub -h localhost -p 1883 \
  -t "smwcs/sensors/<sensor_id>/telemetry" \
  -m '{"fill_pct": 85.0, "temp_c": 27.5, "battery_pct": 80, "rssi": -68, "waste_type": "burnable", "zone_id": "<zone_uuid>"}'

# Check Kafka topics
docker exec smwcs_kafka kafka-topics --bootstrap-server localhost:9092 --list

# Run migrations
cd services/<name>
poetry run alembic upgrade head

# Run tests
poetry run pytest tests/ -v --cov=app

# Dashboard dev server
cd apps/dashboard
npm run dev
```

---

## Ports Reference

| Port | Service |
|---|---|
| 5173 | React dashboard (Vite dev) |
| 5432 | PostgreSQL |
| 6379 | Redis |
| 8001 | auth-service |
| 8002 | bin-registry |
| 8003 | fleet-service |
| 8004 | route-engine (TODO) |
| 8005 | driver-terminal (TODO) |
| 8007 | command-api |
| 8008 | citizen-api (TODO) |
| 8086 | InfluxDB |
| 9000 | MinIO |
| 9001 | MinIO Console |
| 9092 | Kafka |
| 1883 | MQTT (Mosquitto) |
| 27018 | MongoDB (maps to container 27017) |

---

## What NOT to do

- Do not add `django` or `flask` to any service — this codebase uses FastAPI only
- Do not use `asyncio.sleep()` in route handlers
- Do not use `requests` (synchronous) — use `httpx` (async)
- Do not commit `.env` files — only `.env.example`
- Do not create a new Kafka topic without adding it to the topics table in this file
- Do not use `SELECT *` in raw SQL — always name columns explicitly
- Do not store GPS coordinates as plain float columns — use PostGIS POINT geometry
- Do not run multiple Celery beat schedulers — always deploy beat with `replicas: 1`
