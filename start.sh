#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# SMWCS — Smart Municipal Waste Collection System
# Single startup script — starts every service in the correct order
# Usage: ./start.sh
# ─────────────────────────────────────────────────────────────────────────────

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

# Colours
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()    { echo -e "${GREEN}[SMWCS]${NC} $1"; }
warn()    { echo -e "${YELLOW}[SMWCS]${NC} $1"; }
error()   { echo -e "${RED}[SMWCS]${NC} $1"; }
section() { echo -e "\n${GREEN}━━━ $1 ━━━${NC}"; }

# ─────────────────────────────────────────────────────────────────────────────
section "Step 1 — Starting backing services (Docker)"
# ─────────────────────────────────────────────────────────────────────────────

cd "$ROOT"

docker compose up -d \
  postgres influxdb redis mongo \
  kafka zookeeper mosquitto minio

info "Waiting 15 seconds for services to initialise..."
sleep 15

# Verify critical services are healthy
docker compose ps --format "table {{.Name}}\t{{.Status}}" | grep -E "postgres|redis|kafka|influx"

# Start OSRM if not already running
if ! docker ps --format '{{.Names}}' | grep -q smwcs_osrm; then
  if [ -f "$ROOT/infrastructure/osrm/kenya-latest.osrm" ]; then
    info "Starting OSRM routing server..."
    docker run -d --name smwcs_osrm \
      -p 5000:5000 \
      -v "$ROOT/infrastructure/osrm":/data \
      osrm/osrm-backend \
      osrm-routed --algorithm mld /data/kenya-latest.osrm
    sleep 5
    info "OSRM started"
  else
    warn "OSRM map data not found — route engine will use fallback distances"
    warn "To fix: run ./scripts/setup_osrm.sh"
  fi
else
  info "OSRM already running"
fi

# ─────────────────────────────────────────────────────────────────────────────
section "Step 2 — Starting application services"
# ─────────────────────────────────────────────────────────────────────────────

start_service() {
  local name=$1
  local dir=$2
  local cmd=$3
  local port=$4

  info "Starting $name..."
  cd "$ROOT/services/$dir"

  nohup poetry run $cmd \
    > "$LOG_DIR/$name.log" 2>&1 &

  echo $! > "$LOG_DIR/$name.pid"

  if [ -n "$port" ]; then
    # Wait for HTTP service to be ready
    local retries=0
    while ! curl -s "http://localhost:$port/health" > /dev/null 2>&1; do
      sleep 2
      retries=$((retries + 1))
      if [ $retries -ge 15 ]; then
        error "$name failed to start — check logs/$name.log"
        return 1
      fi
    done
    info "$name ready at http://localhost:$port"
  else
    sleep 3
    info "$name started (background)"
  fi
}

# HTTP services — started in dependency order
start_service "auth-service"    "auth-service"    "uvicorn app.main:app --host 0.0.0.0 --port 8001" 8001
start_service "bin-registry"    "bin-registry"    "uvicorn app.main:app --host 0.0.0.0 --port 8002" 8002
start_service "fleet-service"   "fleet-service"   "uvicorn app.main:app --host 0.0.0.0 --port 8003" 8003
start_service "route-engine"    "route-engine"    "uvicorn app.main:app --host 0.0.0.0 --port 8004" 8004
start_service "driver-terminal" "driver-terminal" "uvicorn app.main:app --host 0.0.0.0 --port 8005" 8005
start_service "command-api"     "command-api"     "uvicorn app.main:app --host 0.0.0.0 --port 8007" 8007
start_service "citizen-api"     "citizen-api"     "uvicorn app.main:app --host 0.0.0.0 --port 8008" 8008

# Background services (no HTTP port)
start_service "iot-ingestion"  "iot-ingestion"  "python -m app.main"  ""
start_service "alert-service"  "alert-service"  "python -m app.main"  ""

# ─────────────────────────────────────────────────────────────────────────────
section "Step 3 — Starting analytics (Celery)"
# ─────────────────────────────────────────────────────────────────────────────

cd "$ROOT/services/analytics-service"
VENV=$(poetry env info --path)

info "Starting Celery worker..."
nohup PYTHONPATH=. $VENV/bin/celery \
  -A app.celery_app worker \
  --loglevel=info \
  --concurrency=2 \
  > "$LOG_DIR/analytics-worker.log" 2>&1 &
echo $! > "$LOG_DIR/analytics-worker.pid"

sleep 3

info "Starting Celery beat scheduler..."
nohup PYTHONPATH=. $VENV/bin/celery \
  -A app.celery_app beat \
  --loglevel=info \
  > "$LOG_DIR/analytics-beat.log" 2>&1 &
echo $! > "$LOG_DIR/analytics-beat.pid"

sleep 2
info "Analytics service started"

# ─────────────────────────────────────────────────────────────────────────────
section "Step 4 — Starting dashboard"
# ─────────────────────────────────────────────────────────────────────────────

cd "$ROOT/apps/dashboard"

info "Starting React dashboard..."
nohup npm run dev \
  > "$LOG_DIR/dashboard.log" 2>&1 &
echo $! > "$LOG_DIR/dashboard.pid"

sleep 5
info "Dashboard starting at http://localhost:5173"

# ─────────────────────────────────────────────────────────────────────────────
section "SMWCS is running"
# ─────────────────────────────────────────────────────────────────────────────

echo ""
echo -e "${GREEN}All services started successfully.${NC}"
echo ""
echo "  Dashboard:       http://localhost:5173"
echo "  Auth API:        http://localhost:8001/docs"
echo "  Bin Registry:    http://localhost:8002/docs"
echo "  Fleet Service:   http://localhost:8003/docs"
echo "  Route Engine:    http://localhost:8004/docs"
echo "  Driver Terminal: http://localhost:8005/docs"
echo "  Command API:     http://localhost:8007/docs"
echo "  Citizen API:     http://localhost:8008/docs"
echo "  InfluxDB:        http://localhost:8086"
echo "  MinIO Console:   http://localhost:9001"
echo ""
echo "  Login:  admin@smwcs.co.ke / Admin1234!"
echo ""
echo -e "  Logs:   ${YELLOW}$LOG_DIR/${NC}"
echo -e "  Stop:   ${YELLOW}./stop.sh${NC}"
echo ""
