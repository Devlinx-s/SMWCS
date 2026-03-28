# Project Context
## SMWCS — Smart Municipal Waste Collection System

**Version:** 0.3.0-dev  
**Date:** March 2026  
**Deployment target:** Nairobi, Kenya  
**Build phase:** Phase 2 complete — Core services running  

---

## What This System Does

SMWCS is a real-time waste collection management platform for Nairobi, Kenya.
It replaces manual dispatch and paper-based route planning with a fully automated,
sensor-driven system that:

1. **Monitors bins** — IoT sensors on bins send fill level, temperature, and battery
   readings every 15 minutes via 4G LTE to the platform
2. **Dispatches trucks** — The route engine runs a Capacitated Vehicle Routing Problem
   (CVRP) solver that calculates optimal collection routes based on live fill levels
3. **Guides drivers** — Each truck has an Android tablet running the driver terminal
   app which receives routes and stop instructions via WebSocket in real time
4. **Alerts dispatchers** — The command center dashboard shows live truck positions,
   bin fill levels, and alerts (overflow, fire, low battery, breakdowns)
5. **Serves citizens** — A citizen mobile app shows collection schedules, lets residents
   report problems, and shows live truck location and ETA

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ EDGE LAYER                                                      │
│  nRF9160 bin sensors → 4G LTE → MQTT broker (Mosquitto)         │
│  GPS telematics → 4G LTE → MQTT broker                          │
└───────────────────────┬─────────────────────────────────────────┘
                        │ MQTT publish
┌───────────────────────▼─────────────────────────────────────────┐
│ INGESTION LAYER                                                  │
│  iot-ingestion service                                           │
│  • Validates payloads (Pydantic)                                 │
│  • Writes time-series to InfluxDB                                │
│  • Publishes events to Kafka                                     │
└──────────┬──────────────────────────────────────────────────────┘
           │ Kafka topics
    ┌──────┴─────────────────────────────┐
    │                                    │
┌───▼──────────┐              ┌──────────▼──────────┐
│ alert-service │              │ route-engine         │
│ Consumes:     │              │ Consumes:            │
│ sensor.reading│              │ sensor.reading       │
│ fill.critical │              │ fill.critical        │
│ truck.telem   │              │ Publishes:           │
│ Writes alerts │              │ route.updated        │
│ to PostgreSQL │              │ Uses OR-Tools CVRP   │
└───────────────┘              │ Uses OSRM routing    │
                               └──────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│ APPLICATION LAYER                                                │
│                                                                  │
│  auth-service    → JWT login, RBAC, MFA          port 8001      │
│  bin-registry    → CRUD: zones, bins, sensors    port 8002      │
│  fleet-service   → CRUD: trucks, drivers, shifts port 8003      │
│  command-api     → REST + WebSocket dashboard    port 8007      │
│  driver-terminal → WebSocket for tablet app      port 8005      │
│  citizen-api     → REST for mobile app           port 8008      │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│ INTERFACE LAYER                                                  │
│  dashboard           → React 18 + Vite command center           │
│  driver-terminal-app → React Native Android tablet app          │
│  citizen-app         → React Native iOS/Android                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Stores

| Store | What lives there | Retention |
|---|---|---|
| PostgreSQL 16 + PostGIS | Users, bins, zones, trucks, drivers, shifts, alerts, routes | Permanent |
| InfluxDB 2.7 | Sensor readings (fill %, temp, battery), truck GPS positions | 90 days / 30 days |
| Redis 7 | JWT refresh tokens, rate-limiting counters, route cache | TTL per key |
| MongoDB 7 | Citizen accounts, bin reports, pickup requests | Permanent |
| MinIO | Bin photos, report images, media uploads | Permanent |

---

## Services — Current Status

| Service | Port | Status | Description |
|---|---|---|---|
| auth-service | 8001 | ✅ Complete | JWT login, refresh, logout, MFA setup/verify, RBAC, user CRUD |
| bin-registry | 8002 | ✅ Complete | Zone CRUD with PostGIS polygons, Bin CRUD with GPS points, Sensor registry |
| fleet-service | 8003 | ✅ Complete | Truck CRUD, Driver CRUD, Shift lifecycle (scheduled→active→completed) |
| iot-ingestion | none | ✅ Complete | MQTT subscriber, InfluxDB writer, Kafka publisher, critical fill detection |
| alert-service | none | ✅ Complete | Kafka consumer, threshold rules engine, alert PostgreSQL writer |
| command-api | 8007 | ✅ Complete | Fleet live view, alert management, analytics summary, WebSocket fanout |
| dashboard | 5173 | ✅ Complete | React command center — Dashboard, Fleet, Bins, Alerts, Drivers pages |
| route-engine | 8004 | 🔲 TODO | OR-Tools CVRP solver, OSRM distance matrix, Kafka consumer/publisher |
| driver-terminal | 8005 | 🔲 TODO | WebSocket server for Android tablets, route push, stop completion handler |
| citizen-api | 8008 | 🔲 TODO | Citizen registration, schedule endpoint, bin report, truck ETA |
| analytics-service | none | 🔲 TODO | Celery tasks: hourly zone aggregation, daily driver KPIs |
| media-service | 8012 | 🔲 TODO | MinIO/S3 image upload with Pillow compression |

---

## RBAC — Roles and Permissions

| Role | Permissions |
|---|---|
| `super_admin` | Everything (`*`) |
| `city_admin` | bins:*, trucks:*, drivers:*, routes:*, alerts:*, users:read, zones:*, shifts:* |
| `ops_manager` | routes:*, trucks:*, drivers:*, alerts:*, shifts:*, bins:read |
| `dispatcher` | routes:read, routes:update, trucks:read, alerts:*, bins:read |
| `maintenance_tech` | bins:read, sensors:*, trucks:read |
| `analyst` | analytics:*, reports:*, bins:read, routes:read, trucks:read |

---

## MQTT Topic Schema

```
smwcs / <entity_type> / <entity_id> / <message_type>

Examples:
  smwcs/sensors/SN-NBI-001/telemetry   ← bin sensor reading
  smwcs/sensors/SN-NBI-001/alert       ← sensor-generated alert
  smwcs/trucks/KBZ-001A/position       ← GPS position update
  smwcs/trucks/KBZ-001A/telemetry      ← truck engine/load data
  smwcs/trucks/KBZ-001A/rfid           ← RFID bin scan event
```

### Sensor telemetry payload
```json
{
  "fill_pct":    75.5,
  "weight_kg":   38.2,
  "temp_c":      28.1,
  "battery_pct": 87,
  "rssi":        -65,
  "waste_type":  "burnable",
  "zone_id":     "bc2437c2-eafc-4526-a138-8f9ad2f4ed37"
}
```

### Truck position payload
```json
{
  "lat":       -1.2700,
  "lon":        36.8100,
  "speed_kmh":  35.5,
  "heading":    270,
  "load_kg":    450,
  "fuel_pct":   78.5
}
```

---

## Alert Rules

| Condition | Alert Type | Severity |
|---|---|---|
| fill_pct ≥ 95% | bin_overflow | critical |
| fill_pct ≥ 80% | bin_overflow | high |
| temp_c ≥ 60°C | bin_fire | critical |
| battery_pct < 15% | sensor_low_battery | low |
| rssi < -110 | sensor_offline | medium |
| load_kg > capacity_kg × 0.95 | truck_overload | high |

---

## Pilot Data (loaded during development)

### Zone
- **Westlands Zone A** — `NBI-WEST-A` — Westlands district, Nairobi
- Zone ID: `bc2437c2-eafc-4526-a138-8f9ad2f4ed37`

### Bins
- BIN-NBI-001 through BIN-NBI-005 — all in Westlands Zone A
- Capacity: 240 litres each

### Trucks
| Registration | Make/Model | Status |
|---|---|---|
| KBZ 001A | Isuzu NPR 2022 | on_route |
| KBZ 002B | Isuzu NPR 2022 | available |
| KBZ 003C | Isuzu NPR 2022 | available |

### Drivers
| Employee ID | Name | Phone |
|---|---|---|
| DRV-001 | James Mwangi | +254712345678 |
| DRV-002 | Peter Kamau | +254723456789 |
| DRV-003 | Grace Wanjiku | +254734567890 |

### System Users
| Email | Role |
|---|---|
| admin@smwcs.co.ke | super_admin |
| dispatcher@smwcs.co.ke | dispatcher |

---

## Environment Variables

All services read from their local `.env` file. The root `.env.example` documents all variables.

| Variable | Used by | Value (dev) |
|---|---|---|
| `POSTGRES_PASSWORD` | all services | `smwcs_dev_pass` |
| `REDIS_URL` | auth, command-api | `redis://:smwcs_dev_pass@127.0.0.1:6379` |
| `JWT_SECRET` | auth, all service deps | `smwcs-jwt-secret` |
| `INFLUX_TOKEN` | iot-ingestion, fleet | `smwcs-dev-influx-token` |
| `KAFKA_BROKERS` | iot-ingestion, alerts, command | `localhost:9092` |
| `MQTT_HOST` | iot-ingestion | `localhost` |
| `MQTT_PORT` | iot-ingestion | `1883` |

---

## Kenya-Specific Notes

- All timestamps are stored in UTC in the database
- Display timestamps are converted to `Africa/Nairobi` (UTC+3) in the frontend
- Phone numbers use Kenya format: `+254` prefix
- Waste categories used: burnable, non-burnable, recyclable, organic, hazardous, oversized, electronic
- Mobile network: Safaricom 4G LTE coverage assumed for Nairobi pilot zone
- Map data: Kenya OSM from geofabrik.de (not yet downloaded — required for route engine)
- Currency: KES (Kenyan Shilling) — used in analytics reports
