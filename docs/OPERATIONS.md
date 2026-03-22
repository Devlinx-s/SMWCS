# SMWCS Operations Manual
## How to Start, Stop, and Manage the System

---

## The Short Answer

You need **three commands** to run the entire system:

```bash
cd ~/git/SMWCS

# 1. Start everything
./start.sh

# 2. Check everything is running
./status.sh

# 3. Stop everything
./stop.sh
```

That's it. No 10 terminals. No remembering ports. One command starts all 13 services.

---

## First-Time Setup

Do this once when you first clone the project on a new machine.

### 1. Install system requirements

```bash
# Python 3.11
curl https://pyenv.run | bash
source ~/.bashrc
pyenv install 3.11.9 && pyenv global 3.11.9

# Poetry
pip install pipx && pipx ensurepath && source ~/.bashrc
pipx install poetry

# Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER && newgrp docker
sudo apt install -y docker-compose-plugin

# Node 18
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc
nvm install 18 && nvm use 18

# Enable Docker on boot
sudo systemctl enable docker
```

### 2. Install all Python dependencies

Run this once to install Poetry dependencies for every service:

```bash
cd ~/git/SMWCS

for service in auth-service bin-registry fleet-service iot-ingestion \
               alert-service command-api route-engine driver-terminal \
               citizen-api; do
  echo "Installing $service..."
  cd services/$service && poetry install --no-root && cd ../..
done

# Analytics service needs special handling
cd services/analytics-service
VENV=$(poetry env info --path)
$VENV/bin/pip install celery "celery[redis]" psycopg2-binary \
  pydantic-settings structlog python-dotenv redis
cd ../..

echo "All dependencies installed"
```

### 3. Install dashboard dependencies

```bash
cd ~/git/SMWCS/apps/dashboard
npm install
cd ../..
```

### 4. Set up Kenya OSM routing data (one time only)

```bash
cd ~/git/SMWCS
./scripts/setup_osrm.sh
```

This downloads ~330MB of Kenya map data and processes it. Takes 20–30 minutes.
Only needs to be done once — the processed files persist on disk.

### 5. Disable system services that conflict with Docker

```bash
# These use the same ports as Docker containers
sudo systemctl stop postgresql  && sudo systemctl disable postgresql
sudo systemctl stop redis-server && sudo systemctl disable redis-server
sudo systemctl stop mosquitto   && sudo systemctl disable mosquitto
```

### 6. Load pilot data

```bash
cd ~/git/SMWCS
pip install pymongo --break-system-packages
python3 seed_smwcs.py   # if this file exists
```

Or create the pilot data manually following `docs/project_context.md`.

---

## Daily Usage

### Starting the system

```bash
cd ~/git/SMWCS
./start.sh
```

First run takes about 60 seconds as Docker images start up.
Subsequent runs take about 30 seconds.

When complete you will see:

```
━━━ SMWCS is running ━━━

  Dashboard:       http://localhost:5173
  Auth API:        http://localhost:8001/docs
  Bin Registry:    http://localhost:8002/docs
  Fleet Service:   http://localhost:8003/docs
  Route Engine:    http://localhost:8004/docs
  Driver Terminal: http://localhost:8005/docs
  Command API:     http://localhost:8007/docs
  Citizen API:     http://localhost:8008/docs

  Login:  admin@smwcs.co.ke / Admin1234!
```

### Checking if everything is running

```bash
./status.sh
```

Shows a green ✓ or red ✗ for every service:

```
Application Services:
  ✓  auth-service     →  http://localhost:8001
  ✓  bin-registry     →  http://localhost:8002
  ✓  fleet-service    →  http://localhost:8003
  ✓  route-engine     →  http://localhost:8004
  ✓  driver-terminal  →  http://localhost:8005
  ✓  command-api      →  http://localhost:8007
  ✓  citizen-api      →  http://localhost:8008
  ✓  dashboard        →  http://localhost:5173

Background Services:
  ✓  iot-ingestion
  ✓  alert-service
  ✓  analytics-worker
  ✓  analytics-beat

Infrastructure (Docker):
  ✓  PostgreSQL   →  port 5432
  ✓  InfluxDB     →  port 8086
  ✓  Redis        →  port 6379
  ✓  MongoDB      →  port 27018
  ✓  Kafka        →  port 9092
  ✓  Mosquitto    →  port 1883
  ✓  MinIO        →  port 9000
  ✓  OSRM         →  port 5000
```

### Stopping the system

```bash
# Stop application services, keep databases running
./stop.sh --keep-docker

# Stop everything including databases (data is preserved)
./stop.sh

# Stop everything AND delete all data (fresh start)
./stop.sh --all
```

---

## Viewing Logs

All logs go to the `logs/` folder. Use the log viewer:

```bash
# See available log files
./logs.sh

# Tail a specific service
./logs.sh auth          # auth-service
./logs.sh fleet         # fleet-service
./logs.sh iot           # iot-ingestion
./logs.sh alert         # alert-service
./logs.sh route         # route-engine
./logs.sh terminal      # driver-terminal
./logs.sh command       # command-api
./logs.sh citizen       # citizen-api
./logs.sh analytics-worker
./logs.sh analytics-beat
./logs.sh dashboard

# Tail ALL logs at once
./logs.sh all
```

---

## Restarting a Single Service

If one service crashes or you make a code change:

```bash
# Kill the specific process
pkill -f "uvicorn app.main:app.*8001"   # auth-service
pkill -f "uvicorn app.main:app.*8002"   # bin-registry
pkill -f "uvicorn app.main:app.*8003"   # fleet-service
pkill -f "uvicorn app.main:app.*8004"   # route-engine
pkill -f "uvicorn app.main:app.*8005"   # driver-terminal
pkill -f "uvicorn app.main:app.*8007"   # command-api
pkill -f "uvicorn app.main:app.*8008"   # citizen-api

# Restart it
cd ~/git/SMWCS/services/auth-service
nohup poetry run uvicorn app.main:app --host 0.0.0.0 --port 8001 \
  >> ~/git/SMWCS/logs/auth-service.log 2>&1 &
```

Or just run `./stop.sh --keep-docker && ./start.sh` to restart everything.

---

## Development Mode (with hot reload)

When writing code you want hot reload so the service restarts when you save a file.
Open separate terminals for the services you are working on:

```bash
# Terminal 1 — service you are editing
cd ~/git/SMWCS/services/auth-service
poetry run uvicorn app.main:app --reload --port 8001

# All other services still running in background from ./start.sh
```

The `--reload` flag watches for file changes and restarts automatically.

---

## Testing the System End-to-End

After starting, run this to verify the full pipeline works:

```bash
cd ~/git/SMWCS

# 1. Get admin token
TOKEN=$(curl -s -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@smwcs.co.ke","password":"Admin1234!"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "Token: ${TOKEN:0:30}..."

# 2. Check dashboard summary
curl -s http://localhost:8007/api/v1/analytics/summary \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# 3. Send a test sensor reading
mosquitto_pub -h localhost -p 1883 \
  -t "smwcs/sensors/SN-TEST-001/telemetry" \
  -m '{"fill_pct":88,"temp_c":27,"battery_pct":12,"rssi":-65,
       "waste_type":"burnable","zone_id":"bc2437c2-eafc-4526-a138-8f9ad2f4ed37",
       "lat":-1.2692,"lon":36.8090}'

sleep 3

# 4. Check alerts were created
curl -s "http://localhost:8007/api/v1/alerts/?resolved=false&limit=3" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo "Test complete — check logs/iot-ingestion.log and logs/alert-service.log"
```

---

## Port Reference

| Port | Service | URL |
|---|---|---|
| 5173 | React Dashboard | http://localhost:5173 |
| 5432 | PostgreSQL | psql -h localhost -U smwcs -d smwcs |
| 5000 | OSRM Routing | http://localhost:5000 |
| 6379 | Redis | redis-cli -h localhost -a smwcs_dev_pass |
| 8001 | Auth Service | http://localhost:8001/docs |
| 8002 | Bin Registry | http://localhost:8002/docs |
| 8003 | Fleet Service | http://localhost:8003/docs |
| 8004 | Route Engine | http://localhost:8004/docs |
| 8005 | Driver Terminal | ws://localhost:8005/ws/terminal/{truck_id} |
| 8007 | Command API | http://localhost:8007/docs |
| 8008 | Citizen API | http://localhost:8008/docs |
| 8086 | InfluxDB | http://localhost:8086 |
| 9000 | MinIO API | http://localhost:9000 |
| 9001 | MinIO Console | http://localhost:9001 |
| 9092 | Kafka | localhost:9092 |
| 1883 | MQTT | localhost:1883 |
| 27018 | MongoDB | mongodb://localhost:27018 |

---

## Login Credentials (Development)

| System | URL | Username | Password |
|---|---|---|---|
| Dashboard | http://localhost:5173 | admin@smwcs.co.ke | Admin1234! |
| InfluxDB | http://localhost:8086 | admin | smwcs_dev_pass |
| MinIO Console | http://localhost:9001 | smwcs | smwcs_dev_pass |
| PostgreSQL | port 5432 | smwcs | smwcs_dev_pass |
| Redis | port 6379 | — | smwcs_dev_pass |
| Citizen API | http://localhost:8008 | jane.doe@example.com | Citizen1234! |

---

## What Starts Automatically on System Boot

Docker containers are set to `restart: unless-stopped` so they start
automatically when the machine boots.

Application services (Python + Node) do NOT start automatically on boot.
You need to run `./start.sh` manually after a reboot.

To make the application services start on boot automatically, create a systemd service:

```bash
sudo tee /etc/systemd/system/smwcs.service << EOF
[Unit]
Description=SMWCS Application Services
After=docker.service network.target
Requires=docker.service

[Service]
Type=forking
User=$USER
WorkingDirectory=$HOME/git/SMWCS
ExecStart=$HOME/git/SMWCS/start.sh
ExecStop=$HOME/git/SMWCS/stop.sh
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable smwcs
sudo systemctl start smwcs
```

After this, SMWCS starts automatically on every boot with no manual intervention.

---

## Troubleshooting

### A service won't start

```bash
# Check its log
./logs.sh auth     # or fleet, route, etc.

# Most common causes:
# 1. PostgreSQL not ready yet — wait 10 seconds and run ./start.sh again
# 2. Port already in use — run ./stop.sh then ./start.sh
# 3. Missing .env file — copy from .env.example
```

### Dashboard shows no data

```bash
# Check the command-api is running
curl http://localhost:8007/health

# Check auth is working
curl -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@smwcs.co.ke","password":"Admin1234!"}'
```

### Kafka errors in logs

```bash
# List topics — if empty, Kafka just started and topics need creating
docker exec smwcs_kafka kafka-topics \
  --bootstrap-server localhost:9092 --list

# Recreate all topics
docker exec smwcs_kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --create --if-not-exists --topic bin.sensor.reading --partitions 3 --replication-factor 1

docker exec smwcs_kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --create --if-not-exists --topic bin.fill.critical --partitions 3 --replication-factor 1

docker exec smwcs_kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --create --if-not-exists --topic truck.position --partitions 3 --replication-factor 1

docker exec smwcs_kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --create --if-not-exists --topic alert.created --partitions 3 --replication-factor 1

docker exec smwcs_kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --create --if-not-exists --topic route.updated --partitions 3 --replication-factor 1

docker exec smwcs_kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --create --if-not-exists --topic stop.completed --partitions 3 --replication-factor 1

docker exec smwcs_kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --create --if-not-exists --topic alert.driver --partitions 3 --replication-factor 1

docker exec smwcs_kafka kafka-topics \
  --bootstrap-server localhost:9092 \
  --create --if-not-exists --topic truck.telemetry --partitions 3 --replication-factor 1
```

### Port already in use

```bash
# Find what's using the port
sudo lsof -i :8001   # replace with the conflicting port

# Kill the process
kill <PID>

# Or stop all SMWCS processes
./stop.sh
```

### Reset to a clean state

```bash
./stop.sh --all        # stops everything and deletes all data
./start.sh             # fresh start with empty databases
```

---

## File Locations

```
~/git/SMWCS/
  start.sh              ← Start the entire system
  stop.sh               ← Stop the entire system
  status.sh             ← Check what's running
  logs.sh               ← View service logs
  logs/                 ← All log files written here
    auth-service.log
    fleet-service.log
    iot-ingestion.log
    alert-service.log
    route-engine.log
    driver-terminal.log
    command-api.log
    citizen-api.log
    analytics-worker.log
    analytics-beat.log
    dashboard.log
  scripts/
    setup_osrm.sh        ← Download and process Kenya map data
  docs/
    OPERATIONS.md        ← This file
    AGENTS.md            ← AI agent instructions
    project_context.md   ← Project state
    system.md            ← Technical docs
    api_reference.md     ← All API endpoints
    remaining_work.md    ← What still needs building
    CHANGELOG.md         ← Development history
```
