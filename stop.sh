#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# SMWCS — Stop all services
# Usage: ./stop.sh
#        ./stop.sh --keep-docker    (keep databases running)
#        ./stop.sh --all            (stop everything including Docker volumes)
# ─────────────────────────────────────────────────────────────────────────────

ROOT="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$ROOT/logs"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { echo -e "${GREEN}[SMWCS]${NC} $1"; }
warn() { echo -e "${YELLOW}[SMWCS]${NC} $1"; }

KEEP_DOCKER=false
WIPE_ALL=false

for arg in "$@"; do
  case $arg in
    --keep-docker) KEEP_DOCKER=true ;;
    --all)         WIPE_ALL=true ;;
  esac
done

info "Stopping SMWCS application services..."

# Stop all services by PID file
SERVICES=(
  auth-service
  bin-registry
  fleet-service
  route-engine
  driver-terminal
  command-api
  citizen-api
  iot-ingestion
  alert-service
  analytics-worker
  analytics-beat
  dashboard
)

for svc in "${SERVICES[@]}"; do
  PID_FILE="$LOG_DIR/$svc.pid"
  if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
      kill "$PID" 2>/dev/null
      info "Stopped $svc (pid $PID)"
    fi
    rm -f "$PID_FILE"
  fi
done

# Kill any remaining uvicorn / celery processes for this project
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "celery.*smwcs"        2>/dev/null || true
pkill -f "python -m app.main"   2>/dev/null || true

# Stop OSRM container
if docker ps --format '{{.Names}}' | grep -q smwcs_osrm; then
  docker stop smwcs_osrm > /dev/null 2>&1
  docker rm   smwcs_osrm > /dev/null 2>&1
  info "Stopped OSRM"
fi

# Docker handling
if [ "$WIPE_ALL" = true ]; then
  warn "Stopping Docker services AND deleting all data volumes..."
  cd "$ROOT"
  docker compose down -v
  info "All Docker services and volumes removed"

elif [ "$KEEP_DOCKER" = false ]; then
  info "Stopping Docker services (data preserved)..."
  cd "$ROOT"
  docker compose down
  info "Docker services stopped"

else
  info "Docker services kept running (--keep-docker)"
fi

info "SMWCS stopped."
echo ""
echo "  To start again:        ./start.sh"
echo "  To view logs:          ls logs/"
echo "  To wipe all data:      ./stop.sh --all"
echo ""
