#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# SMWCS — Check status of all services
# Usage: ./status.sh
# ─────────────────────────────────────────────────────────────────────────────

ROOT="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$ROOT/logs"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC}  $1"; }
fail() { echo -e "  ${RED}✗${NC}  $1"; }
warn() { echo -e "  ${YELLOW}~${NC}  $1"; }

echo ""
echo -e "${GREEN}━━━ SMWCS Service Status ━━━${NC}"
echo ""

# ── HTTP services ─────────────────────────────────────────────────────────────
echo "Application Services:"

check_http() {
  local name=$1
  local port=$2
  if curl -s "http://localhost:$port/health" > /dev/null 2>&1; then
    ok "$name  →  http://localhost:$port"
  else
    fail "$name  →  NOT RESPONDING on port $port"
  fi
}

check_http "auth-service    " 8001
check_http "bin-registry    " 8002
check_http "fleet-service   " 8003
check_http "route-engine    " 8004
check_http "driver-terminal " 8005
check_http "command-api     " 8007
check_http "citizen-api     " 8008
check_http "media-service   " 8012
check_http "dashboard       " 5173

echo ""
echo "Background Services:"

check_pid() {
  local name=$1
  local service_name=$(echo "$1" | xargs)  # trim whitespace
  local pid_file="$LOG_DIR/$service_name.pid"
  if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    ok "$name  (pid $(cat "$pid_file"))"
  else
    fail "$name  NOT RUNNING"
  fi
}

check_pid "iot-ingestion   "
check_pid "alert-service   "
check_pid "analytics-worker"
check_pid "analytics-beat  "

echo ""
echo "Infrastructure (Docker):"

check_docker() {
  local name=$1
  local container=$2
  local port=$3
  if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "$container"; then
    ok "$name  →  port $port"
  else
    fail "$name  NOT RUNNING"
  fi
}

check_docker "PostgreSQL  " smwcs_postgres 5432
check_docker "InfluxDB    " smwcs_influx   8086
check_docker "Redis       " smwcs_redis    6379
check_docker "MongoDB     " smwcs_mongo    27018
check_docker "Kafka       " smwcs_kafka    9092
check_docker "Mosquitto   " smwcs_mqtt     1883
check_docker "MinIO       " smwcs_minio    9000
check_docker "OSRM        " smwcs_osrm     5000

echo ""
echo "Quick Links:"
echo "  Dashboard:     http://localhost:5173   (admin@smwcs.co.ke / Admin1234!)"
echo "  InfluxDB:      http://localhost:8086   (admin / smwcs_dev_pass)"
echo "  MinIO:         http://localhost:9001   (smwcs / smwcs_dev_pass)"
echo ""
echo "Logs:  $LOG_DIR/"
echo ""
