#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# SMWCS — Download and process Kenya OSM data for OSRM routing
# Run this once to set up the routing server.
# Takes about 30 minutes total (mostly download time).
# ─────────────────────────────────────────────────────────────────────────────

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OSRM_DIR="$ROOT/infrastructure/osrm"

GREEN='\033[0;32m'
NC='\033[0m'
info() { echo -e "${GREEN}[OSRM]${NC} $1"; }

mkdir -p "$OSRM_DIR"
cd "$OSRM_DIR"

# Step 1 — Download Kenya OSM data
if [ ! -f "kenya-latest.osm.pbf" ]; then
  info "Downloading Kenya OSM data (~330MB)..."
  wget -O kenya-latest.osm.pbf \
    https://download.geofabrik.de/africa/kenya-latest.osm.pbf
else
  info "kenya-latest.osm.pbf already exists — skipping download"
fi

# Step 2 — Extract
if [ ! -f "kenya-latest.osrm" ]; then
  info "Step 1/3: Extracting road network (5-15 minutes)..."
  docker run -t -v "$(pwd)":/data osrm/osrm-backend \
    osrm-extract -p /opt/car.lua /data/kenya-latest.osm.pbf
else
  info "kenya-latest.osrm already exists — skipping extract"
fi

# Step 3 — Partition
if [ ! -f "kenya-latest.osrm.partition" ]; then
  info "Step 2/3: Partitioning (2-5 minutes)..."
  docker run -t -v "$(pwd)":/data osrm/osrm-backend \
    osrm-partition /data/kenya-latest.osrm
fi

# Step 4 — Customize
if [ ! -f "kenya-latest.osrm.cell_metrics" ]; then
  info "Step 3/3: Customizing (1-2 minutes)..."
  docker run -t -v "$(pwd)":/data osrm/osrm-backend \
    osrm-customize /data/kenya-latest.osrm
fi

# Step 5 — Start server
info "Starting OSRM server..."
docker rm -f smwcs_osrm 2>/dev/null || true
docker run -d --name smwcs_osrm \
  -p 5000:5000 \
  -v "$(pwd)":/data \
  osrm/osrm-backend \
  osrm-routed --algorithm mld /data/kenya-latest.osrm

sleep 5

# Test
info "Testing OSRM — routing Nairobi CBD to Westlands..."
RESULT=$(curl -s "http://localhost:5000/route/v1/driving/36.8219,-1.2921;36.8089,-1.2634")
if echo "$RESULT" | grep -q '"code":"Ok"'; then
  info "OSRM working correctly"
  DURATION=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(round(d['routes'][0]['duration']/60,1))")
  info "Test route: Nairobi CBD → Westlands = $DURATION minutes"
else
  echo "OSRM test failed. Check docker logs smwcs_osrm"
fi
