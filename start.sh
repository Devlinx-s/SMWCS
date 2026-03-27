#!/bin/bash
ROOT="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${GREEN}[SMWCS]${NC} $1"; }
warn()    { echo -e "${YELLOW}[SMWCS]${NC} $1"; }
section() { echo -e "\n${GREEN}━━━ $1 ━━━${NC}"; }

# ── Step 1: Docker backing services ──────────────────────────────────────────
section "Step 1 — Starting backing services (Docker)"
cd "$ROOT"
docker compose up -d postgres influxdb redis mongo kafka zookeeper mosquitto minio 2>&1 || true

info "Waiting 30 seconds for databases to initialise..."
sleep 30

docker compose ps --format "table {{.Name}}\t{{.Status}}" | grep -E "postgres|redis|kafka|influx" || true

# OSRM
if docker ps --format '{{.Names}}' | grep -q smwcs_osrm; then
  info "OSRM already running"
elif [ -f "$ROOT/infrastructure/osrm/kenya-latest.osrm" ]; then
  info "Starting OSRM routing server..."
  docker rm -f smwcs_osrm 2>/dev/null || true
  docker run -d --name smwcs_osrm \
    -p 5000:5000 \
    -v "$ROOT/infrastructure/osrm":/data \
    osrm/osrm-backend \
    osrm-routed --algorithm mld /data/kenya-latest.osrm
  sleep 5
  info "OSRM started"
else
  warn "OSRM map data not found — route engine will use Euclidean fallback"
fi

# ── Step 2: Application services ─────────────────────────────────────────────
section "Step 2 — Starting application services"

start_http() {
  local name=$1 dir=$2 cmd=$3 port=$4
  info "Starting $name..."
  cd "$ROOT/services/$dir"
  nohup poetry run $cmd > "$LOG_DIR/$name.log" 2>&1 &
  echo $! > "$LOG_DIR/$name.pid"
  local retries=0
  while ! curl -s "http://localhost:$port/health" > /dev/null 2>&1; do
    sleep 2
    retries=$((retries + 1))
    if [ $retries -ge 25 ]; then
      warn "$name slow to start — continuing anyway (check logs/$name.log)"
      return 0
    fi
  done
  info "$name ready  →  http://localhost:$port"
}

start_bg() {
  local name=$1 dir=$2 cmd=$3
  info "Starting $name..."
  cd "$ROOT/services/$dir"
  nohup poetry run $cmd > "$LOG_DIR/$name.log" 2>&1 &
  echo $! > "$LOG_DIR/$name.pid"
  sleep 3
  info "$name started"
}

start_http "auth-service"    "auth-service"    "uvicorn app.main:app --host 0.0.0.0 --port 8001" 8001
start_http "bin-registry"    "bin-registry"    "uvicorn app.main:app --host 0.0.0.0 --port 8002" 8002
start_http "fleet-service"   "fleet-service"   "uvicorn app.main:app --host 0.0.0.0 --port 8003" 8003
start_http "route-engine"    "route-engine"    "uvicorn app.main:app --host 0.0.0.0 --port 8004" 8004
start_http "driver-terminal" "driver-terminal" "uvicorn app.main:app --host 0.0.0.0 --port 8005" 8005
start_http "command-api"     "command-api"     "uvicorn app.main:app --host 0.0.0.0 --port 8007" 8007
start_http "citizen-api"     "citizen-api"     "uvicorn app.main:app --host 0.0.0.0 --port 8008" 8008

start_bg "iot-ingestion" "iot-ingestion" "python -m app.main"
start_bg "alert-service" "alert-service" "python -m app.main"

# ── Step 3: Celery analytics ──────────────────────────────────────────────────
section "Step 3 — Starting analytics (Celery)"
cd "$ROOT/services/analytics-service"
ANALYTICS_VENV=$(poetry env info --path 2>/dev/null)

if [ -n "$ANALYTICS_VENV" ] && [ -f "$ANALYTICS_VENV/bin/celery" ]; then
  info "Starting Celery worker..."
  nohup env PYTHONPATH=. "$ANALYTICS_VENV/bin/celery" \
    -A app.celery_app worker --loglevel=info --concurrency=2 \
    > "$LOG_DIR/analytics-worker.log" 2>&1 &
  echo $! > "$LOG_DIR/analytics-worker.pid"
  sleep 4

  info "Starting Celery beat..."
  nohup env PYTHONPATH=. "$ANALYTICS_VENV/bin/celery" \
    -A app.celery_app beat --loglevel=info \
    > "$LOG_DIR/analytics-beat.log" 2>&1 &
  echo $! > "$LOG_DIR/analytics-beat.pid"
  sleep 2
  info "Analytics started"
else
  warn "Analytics venv not found — skipping Celery (run manually if needed)"
fi

# ── Step 4: Dashboard ─────────────────────────────────────────────────────────
section "Step 4 — Starting dashboard"
cd "$ROOT/apps/dashboard"
nohup npm run dev > "$LOG_DIR/dashboard.log" 2>&1 &
echo $! > "$LOG_DIR/dashboard.pid"
sleep 6

# ── Done ──────────────────────────────────────────────────────────────────────
section "SMWCS is running"
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
echo -e "  Logs:   ${YELLOW}./logs.sh <service-name>${NC}"
echo -e "  Status: ${YELLOW}./status.sh${NC}"
echo -e "  Stop:   ${YELLOW}./stop.sh${NC}"
echo ""
