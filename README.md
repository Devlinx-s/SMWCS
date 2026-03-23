# SMWCS
## Smart Municipal Waste Collection System — Nairobi, Kenya

A real-time waste collection management platform that uses IoT sensors, live GPS tracking,
and an AI route optimisation engine to automate municipal waste collection.

---

## Current Status — Phase 2 Complete

| Service | Port | Status |
|---|---|---|
| Auth Service | 8001 | ✅ Running |
| Bin Registry | 8002 | ✅ Running |
| Fleet Service | 8003 | ✅ Running |
| IoT Ingestion | — | ✅ Running |
| Alert Service | — | ✅ Running |
| Command API | 8007 | ✅ Running |
| React Dashboard | 5173 | ✅ Running |
| Route Engine | 8004 | 🔲 TODO |
| Driver Terminal | 8005 | 🔲 TODO |
| Citizen API | 8008 | 🔲 TODO |
| Analytics Service | — | 🔲 TODO |

---

## Quick Start

### Prerequisites
- Python 3.11 (via pyenv)
- Poetry 2.0+
- Docker + Docker Compose v2
- Node.js 18 (via nvm)

### 1. Start backing services
```bash
docker compose up -d postgres influxdb redis mongo kafka zookeeper mosquitto minio
```

### 2. Start application services (one terminal each)
```bash
# Auth
cd services/auth-service && poetry run uvicorn app.main:app --reload --port 8001

# Bins
cd services/bin-registry && poetry run uvicorn app.main:app --reload --port 8002

# Fleet
cd services/fleet-service && poetry run uvicorn app.main:app --reload --port 8003

# IoT
cd services/iot-ingestion && poetry run python -m app.main

# Alerts
cd services/alert-service && poetry run python -m app.main

# Command API
cd services/command-api && poetry run uvicorn app.main:app --reload --port 8007
```

### 3. Start dashboard
```bash
cd apps/dashboard && npm run dev
```

### 4. Open dashboard
Go to **http://localhost:5173**

Login: `admin@smwcs.co.ke` / `Admin1234!`

---

## API Documentation
- Auth: http://localhost:8001/docs
- Bins: http://localhost:8002/docs
- Fleet: http://localhost:8003/docs
- Command: http://localhost:8007/docs

---

## Documentation
- [`docs/AGENTS.md`](docs/AGENTS.md) — AI agent instructions for this codebase
- [`docs/project_context.md`](docs/project_context.md) — Project state and context
- [`docs/system.md`](docs/system.md) — Full technical system documentation
- [`docs/api_reference.md`](docs/api_reference.md) — All API endpoints
- [`docs/CHANGELOG.md`](docs/CHANGELOG.md) — Development history

---

## Architecture Overview

```
IoT Sensors → MQTT → iot-ingestion → InfluxDB (time-series)
                                   → Kafka → alert-service → PostgreSQL
                                           → route-engine  → driver-terminal
                                           → command-api   → React dashboard (WebSocket)
```

---

## Environment Setup
Copy `.env.example` to `.env` in each service directory:
```bash
cp .env.example services/auth-service/.env
# edit with real values for production
