#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# SMWCS — View logs
# Usage:
#   ./logs.sh                    show all available log files
#   ./logs.sh auth               tail auth-service log
#   ./logs.sh fleet              tail fleet-service log
#   ./logs.sh all                tail ALL logs at once
# ─────────────────────────────────────────────────────────────────────────────

ROOT="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$ROOT/logs"

if [ ! -d "$LOG_DIR" ]; then
  echo "No logs directory found. Has SMWCS been started? Run ./start.sh first."
  exit 1
fi

SERVICE=$1

if [ -z "$SERVICE" ]; then
  echo ""
  echo "Available logs:"
  ls "$LOG_DIR"/*.log 2>/dev/null | while read f; do
    size=$(du -sh "$f" 2>/dev/null | cut -f1)
    echo "  $(basename "$f" .log)  ($size)"
  done
  echo ""
  echo "Usage:"
  echo "  ./logs.sh auth              tail auth-service"
  echo "  ./logs.sh fleet             tail fleet-service"
  echo "  ./logs.sh iot               tail iot-ingestion"
  echo "  ./logs.sh alert             tail alert-service"
  echo "  ./logs.sh route             tail route-engine"
  echo "  ./logs.sh terminal          tail driver-terminal"
  echo "  ./logs.sh command           tail command-api"
  echo "  ./logs.sh citizen           tail citizen-api"
  echo "  ./logs.sh analytics-worker  tail Celery worker"
  echo "  ./logs.sh analytics-beat    tail Celery beat"
  echo "  ./logs.sh dashboard         tail React dashboard"
  echo "  ./logs.sh all               tail everything"
  echo ""
  exit 0
fi

# Map short names to log files
case $SERVICE in
  auth)             LOG="$LOG_DIR/auth-service.log" ;;
  bins|bin)         LOG="$LOG_DIR/bin-registry.log" ;;
  fleet)            LOG="$LOG_DIR/fleet-service.log" ;;
  iot)              LOG="$LOG_DIR/iot-ingestion.log" ;;
  alert|alerts)     LOG="$LOG_DIR/alert-service.log" ;;
  route)            LOG="$LOG_DIR/route-engine.log" ;;
  terminal)         LOG="$LOG_DIR/driver-terminal.log" ;;
  command)          LOG="$LOG_DIR/command-api.log" ;;
  citizen)          LOG="$LOG_DIR/citizen-api.log" ;;
  analytics-worker) LOG="$LOG_DIR/analytics-worker.log" ;;
  analytics-beat)   LOG="$LOG_DIR/analytics-beat.log" ;;
  dashboard)        LOG="$LOG_DIR/dashboard.log" ;;
  all)
    tail -f "$LOG_DIR"/*.log
    exit 0
    ;;
  *)
    # Try exact match
    LOG="$LOG_DIR/$SERVICE.log"
    ;;
esac

if [ ! -f "$LOG" ]; then
  echo "Log file not found: $LOG"
  echo "Run ./logs.sh to see available logs."
  exit 1
fi

echo "Tailing $LOG  (Ctrl+C to stop)"
echo "────────────────────────────────"
tail -f "$LOG"
