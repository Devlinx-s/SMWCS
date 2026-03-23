#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# SMWCS — Start all services
# Usage: ./start.sh
# ─────────────────────────────────────────────────────────────────────────────

ROOT="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

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

# Free port 1883 if something else is using it
if lsof -i :1883 -t &>/dev/null; then
  warn "Port 1883 in use — killing conflicting process..."
  sudo kill -9 $(lsof -i :1883 -t) 2>/dev/null || true
  sleep 1
fi

docker compose up -d \
  postgres influxdb redis mongo \
  kafka zookeeper mosquitto minio

info "Waiting 15 seconds for services to initialise..."
sleep 15

docker compose ps --format "table {{.Name}}\t{{.Status}}" | grep -E "postgres|redis|kafka|influx"

# ─────────────────────────────────────────────────────────────────────────────
section "Step 2 — Starting OSRM routing server"
# ─────────────────────────────────────────────────────────────────────────────

# Remove stale OSRM container if it exists (stopped or running)
if docker ps -a --format '{{.Names}}' | grep -q '^smwcs_osrm$'; then
  STATE=$(docker inspect -f '{{.State.Status}}' smwcs_osrm 2>/dev/null)
  if [ "$STATE" = "running" ]; then
    info "OSRM already running"
  else
    info "Removing stale OSRM container..."
    docker rm smwcs_osrm > /dev/null 2>&1
    STATE=""
  fi
fi

if [ "$STATE" != "running" ]; then
  if [ -f "$ROOT/infrastructure/osrm/kenya-latest.osrm" ]; then
    info "Starting OSRM routing server..."
    docker run -d --name smwcs_osrm \
      -p 5000:5000 \
      -v "$ROOT/infrastructure/osrm":/data \
      osrm/osrm-backend \
      osrm-routed --algorithm mld /data/kenya-latest.osrm > /dev/null 2>&1
    sleep 5
    info "OSRM started"
  else
    warn "OSRM map data not found — route engine will use fallback distances"
    warn "To fix: run ./scripts/setup_osrm.sh"
  fi
fi

# ─────────────────────────────────────────────────────────────────────────────
section "Step 3 — Starting application services"
# ─────────────────────────────────────────────────────────────────────────────

start_http_service() {
  local name=$1
  local dir=$2
  local port=$3

  info "Starting $name..."
  cd "$ROOT/services/$dir"

  nohup poetry run uvicorn app.main:app \
    --host 0.0.0.0 --port "$port" \
    > "$LOG_DIR/$name.log" 2>&1 &

  echo $! > "$LOG_DIR/$name.pid"

  local retries=0
  while ! curl -s "http://localhost:$port/health" > /dev/null 2>&1; do
    sleep 2
    retries=$((retries + 1))
    if [ $retries -ge 20 ]; then
      error "$name failed to start — check: ./logs.sh $name"
      return 1
    fi
  done
  info "$name ready   http://localhost:$port"
}

start_bg_service() {
  local name=$1
  local dir=$2
  local cmd=$3

  info "Starting $name..."
  cd "$ROOT/services/$dir"

  nohup poetry run $cmd \
    > "$LOG_DIR/$name.log" 2>&1 &

  echo $! > "$LOG_DIR/$name.pid"
  sleep 3
  info "$name started"
}

start_http_service "auth-service"    "auth-service"    8001
start_http_service "bin-registry"    "bin-registry"    8002
start_http_service "fleet-service"   "fleet-service"   8003
start_http_service "route-engine"    "route-engine"    8004
start_http_service "driver-terminal" "driver-terminal" 8005
start_http_service "command-api"     "command-api"     8007
start_http_service "citizen-api"     "citizen-api"     8008

start_bg_service "iot-ingestion" "iot-ingestion" "python -m app.main"
start_bg_service "alert-service" "alert-service" "python -m app.main"

# ─────────────────────────────────────────────────────────────────────────────
section "Step 4 — Starting analytics (Celery)"
# ─────────────────────────────────────────────────────────────────────────────

cd "$ROOT/services/analytics-service"

info "Starting Celery worker..."
nohup bash -c 'export PYTHONPATH=. && poetry run celery -A app.celery_app worker --loglevel=info --concurrency=2' \
  > "$LOG_DIR/analytics-worker.log" 2>&1 &
echo $! > "$LOG_DIR/analytics-worker.pid"
sleep 3

info "Starting Celery beat scheduler..."
nohup bash -c 'export PYTHONPATH=. && poetry run celery -A app.celery_app beat --loglevel=info' \
  > "$LOG_DIR/analytics-beat.log" 2>&1 &
echo $! > "$LOG_DIR/analytics-beat.pid"
sleep 2
info "Analytics started"

# ─────────────────────────────────────────────────────────────────────────────
section "Step 5 — Starting dashboard"
# ─────────────────────────────────────────────────────────────────────────────

cd "$ROOT/apps/dashboard"
info "Starting React dashboard..."
nohup npm run dev \
  > "$LOG_DIR/dashboard.log" 2>&1 &
echo $! > "$LOG_DIR/dashboard.pid"
sleep 6
info "Dashboard starting at http://localhost:5173"

# ─────────────────────────────────────────────────────────────────────────────
section "SMWCS is running"
# ─────────────────────────────────────────────────────────────────────────────

echo ""
echo -e "${GREEN}All services started.${NC}"
echo ""
echo "  Dashboard:       http://localhost:5173"
echo "  Auth API:        http://localhost:8001/docs"
echo "  Bin Registry:    http://localhost:8002/docs"
echo "  Fleet Service:   http://localhost:8003/docs"
echo "  Route Engine:    http://localhost:8004/docs"
echo "  Driver Terminal: http://localhost:8005/docs"
echo "  Command API:     http://localhost:8007/docs"
echo "  Citizen API:     http://localhost:8008/docs"
echo ""
echo "  Login:  admin@smwcs.co.ke / Admin1234!"
echo ""
echo -e "  Logs:  ${YELLOW}./logs.sh <service>${NC}   or   ${YELLOW}./logs.sh all${NC}"
echo -e "  Stop:  ${YELLOW}./stop.sh${NC}"
echo ""
