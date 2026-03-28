# API Reference
## SMWCS — All Services

Base URLs (development):
- Auth:        http://localhost:8001
- Bin Registry: http://localhost:8002
- Fleet:       http://localhost:8003
- Command:     http://localhost:8007

All authenticated endpoints require:
```
Authorization: Bearer <access_token>
```

---

## Authentication

### POST /api/v1/auth/login
Get JWT tokens.

**Request:**
```json
{
  "email":     "admin@smwcs.co.ke",
  "password":  "Admin1234!",
  "totp_code": "123456"  // optional — required if MFA enabled
}
```

**Response 200:**
```json
{
  "access_token":  "eyJhbGci...",
  "refresh_token": "a1b2c3d4-...",
  "token_type":    "bearer",
  "user": {
    "id":          "e861ef89-...",
    "email":       "admin@smwcs.co.ke",
    "first_name":  "System",
    "last_name":   "Admin",
    "role":        "super_admin",
    "is_active":   true,
    "mfa_enabled": false,
    "last_login":  "2026-03-22T07:54:20Z",
    "created_at":  "2026-03-22T07:36:39Z"
  }
}
```

**Errors:**
- `401` — wrong email/password or invalid TOTP
- `403` — account deactivated or MFA required but no code given

---

### POST /api/v1/auth/refresh
Exchange refresh token for new access token.

**Request:**
```json
{ "refresh_token": "a1b2c3d4-..." }
```

**Response 200:**
```json
{ "access_token": "eyJhbGci...", "token_type": "bearer" }
```

---

### POST /api/v1/auth/logout
Invalidate refresh token.

**Request:**
```json
{ "refresh_token": "a1b2c3d4-..." }
```

**Response 200:**
```json
{ "message": "Logged out successfully" }
```

---

### GET /api/v1/auth/me
Get current user profile.

**Response 200:** UserResponse (same as login user object)

---

### POST /api/v1/auth/mfa/setup
Generate TOTP secret and QR code.

**Response 200:**
```json
{
  "secret":  "JBSWY3DPEHPK3PXP",
  "qr_code": "iVBORw0KGgo..."  // base64 PNG
}
```

---

### POST /api/v1/auth/mfa/verify
Enable MFA after scanning QR code.

**Request:**
```json
{ "totp_code": "123456" }
```

**Response 200:**
```json
{ "message": "MFA enabled successfully" }
```

---

### POST /api/v1/users/
Create new system user. Requires `users:read`.

**Request:**
```json
{
  "email":      "dispatcher@smwcs.co.ke",
  "password":   "Dispatch1234!",
  "first_name": "John",
  "last_name":  "Kamau",
  "role":       "dispatcher"
}
```

Valid roles: `super_admin`, `city_admin`, `ops_manager`, `dispatcher`, `maintenance_tech`, `analyst`

---

## Bin Registry

### GET /api/v1/zones/
List all zones. Requires `bins:read`.

**Response 200:**
```json
[
  {
    "id":         "bc2437c2-...",
    "name":       "Westlands Zone A",
    "code":       "NBI-WEST-A",
    "district":   "Westlands",
    "population": 45000,
    "created_at": "2026-03-22T08:25:16Z"
  }
]
```

---

### POST /api/v1/zones/
Create zone with PostGIS boundary. Requires `zones:write`.

**Request:**
```json
{
  "name":       "Westlands Zone A",
  "code":       "NBI-WEST-A",
  "district":   "Westlands",
  "population": 45000,
  "boundary": {
    "type": "Polygon",
    "coordinates": [[
      [36.800, -1.260],
      [36.820, -1.260],
      [36.820, -1.280],
      [36.800, -1.280],
      [36.800, -1.260]
    ]]
  }
}
```

---

### GET /api/v1/bins/
List bins. Requires `bins:read`.

**Query params:**
- `zone_id` — filter by zone UUID
- `status` — filter by status (active/maintenance/decommissioned/pending_install)
- `page` — page number (default: 1)
- `per_page` — results per page (default: 50, max: 200)

**Response 200:**
```json
[
  {
    "id":              "257c3ca5-...",
    "zone_id":         "bc2437c2-...",
    "sensor_id":       null,
    "serial_number":   "BIN-NBI-001",
    "address":         "Westlands Road, Nairobi",
    "capacity_litres": 240,
    "status":          "active",
    "install_date":    null,
    "last_serviced":   null,
    "notes":           null,
    "created_at":      "2026-03-22T08:26:28Z",
    "latest_fill_pct": null
  }
]
```

---

### POST /api/v1/bins/
Register a bin. Requires `bins:write`.

**Request:**
```json
{
  "serial_number":   "BIN-NBI-006",
  "location":        { "lat": -1.2692, "lon": 36.8090 },
  "zone_id":         "bc2437c2-...",
  "address":         "Parklands Road, Nairobi",
  "capacity_litres": 120
}
```

---

### GET /api/v1/bins/zone/{zone_id}/summary
Fill level summary for a zone. Requires `bins:read`.

**Response 200:**
```json
{
  "zone_id":        "bc2437c2-...",
  "total":          5,
  "below_50":       3,
  "between_50_80":  1,
  "above_80":       1,
  "critical":       0
}
```

---

## Fleet Service

### GET /api/v1/trucks/
List trucks. Requires `trucks:read`.

**Query params:** `status` — filter by status

**Response 200:**
```json
[
  {
    "id":              "b43d062c-...",
    "registration":    "KBZ 001A",
    "make":            "Isuzu",
    "model":           "NPR",
    "year":            2022,
    "capacity_kg":     3000,
    "fuel_type":       "diesel",
    "status":          "on_route",
    "current_load_kg": 0,
    "gps_unit_id":     null,
    "created_at":      "2026-03-22T08:38:06Z"
  }
]
```

---

### POST /api/v1/trucks/
Register a truck. Requires `trucks:write`.

**Request:**
```json
{
  "registration":    "KBZ 004D",
  "make":            "Isuzu",
  "model":           "NPR",
  "year":            2023,
  "capacity_kg":     3500,
  "capacity_litres": 8000,
  "fuel_type":       "diesel",
  "gps_unit_id":     "GPS-004"
}
```

---

### POST /api/v1/drivers/
Register a driver. Requires `drivers:write`.

**Request:**
```json
{
  "employee_id":    "DRV-004",
  "first_name":     "Mary",
  "last_name":      "Njeri",
  "phone":          "+254745678901",
  "email":          "m.njeri@smwcs.co.ke",
  "license_number": "DL-NBI-004",
  "license_expiry": "2027-12-31"
}
```

---

### POST /api/v1/shifts/
Create a shift. Requires `shifts:write`.

**Request:**
```json
{
  "truck_id":      "b43d062c-...",
  "driver_id":     "ed530fed-...",
  "planned_start": "2026-03-23T07:00:00Z",
  "planned_end":   "2026-03-23T15:00:00Z",
  "notes":         "Westlands Zone A morning shift"
}
```

---

### POST /api/v1/shifts/{id}/start
Start a scheduled shift. Requires `shifts:write`.
Side effect: sets truck status → `on_route`.

---

### POST /api/v1/shifts/{id}/end
End an active shift. Requires `shifts:write`.
Side effect: sets truck status → `available`.

---

## Command API

### GET /api/v1/fleet/live
All trucks with driver and shift info. Requires `trucks:read`.

**Response 200:**
```json
[
  {
    "id":           "b43d062c-...",
    "registration": "KBZ 001A",
    "make":         "Isuzu",
    "model":        "NPR",
    "status":       "on_route",
    "current_load_kg": 0,
    "capacity_kg":  3000,
    "fuel_type":    "diesel",
    "gps_unit_id":  null,
    "load_pct":     0.0,
    "driver_name":  "James Mwangi",
    "driver_phone": "+254712345678",
    "shift_id":     "48448a17-...",
    "planned_start":"2026-03-22T07:00:00Z",
    "planned_end":  "2026-03-22T15:00:00Z"
  }
]
```

---

### GET /api/v1/alerts/
List alerts. Requires `alerts:read`.

**Query params:**
- `resolved` — true/false
- `severity` — critical/high/medium/low
- `zone_id` — filter by zone
- `limit` — max results (default: 50, max: 200)

**Response 200:**
```json
[
  {
    "id":           "618e9789-...",
    "type":         "bin_overflow",
    "severity":     "high",
    "sensor_id":    "SN-NBI-003",
    "truck_id":     null,
    "zone_id":      "bc2437c2-...",
    "message":      "Bin SN-NBI-003 at 88.0% — collection needed soon",
    "acknowledged": false,
    "resolved":     false,
    "created_at":   "2026-03-22T14:13:47Z"
  }
]
```

---

### GET /api/v1/analytics/summary
System-wide summary. Requires `analytics:read`.

**Response 200:**
```json
{
  "trucks":  { "trucks_active": 1, "trucks_total": 3 },
  "bins":    { "bins_total": 5, "bins_active": 5 },
  "alerts":  { "open_alerts": 2, "critical_alerts": 0 },
  "drivers": { "drivers_active": 3 }
}
```

---

## WebSocket

### WS /ws/dashboard
Real-time event stream for the command dashboard.

**Connection:** No auth required on the WebSocket itself (token validated on REST endpoints).

**Keepalive:** Client sends `ping` text every 30 seconds. Server replies `pong`.

**Server push frames:**
```json
// Truck position update
{ "type": "TRUCK_POSITION", "data": { "truck_id": "...", "lat": -1.27, "lon": 36.81, "speed_kmh": 35 } }

// New alert
{ "type": "ALERT_CREATED", "data": { "alert_id": "...", "type": "bin_overflow", "severity": "high", "message": "..." } }

// Bin critical fill
{ "type": "BIN_FILL_CRITICAL", "data": { "sensor_id": "...", "fill_pct": 92.0, "zone_id": "..." } }

// Route updated (after route-engine built)
{ "type": "ROUTE_UPDATED", "data": { "truck_id": "...", "zone_id": "...", "stops": [...] } }
```

---

## MQTT (for sensors and GPS units)

**Broker:** localhost:1883 (dev) — no auth  
**Production:** TLS on port 8883 with password file

### Publish sensor telemetry
```bash
mosquitto_pub -h localhost -p 1883 \
  -t "smwcs/sensors/<sensor_id>/telemetry" \
  -m '{
    "fill_pct":    75.5,
    "weight_kg":   38.2,
    "temp_c":      28.1,
    "battery_pct": 87,
    "rssi":        -65,
    "waste_type":  "burnable",
    "zone_id":     "bc2437c2-..."
  }'
```

### Publish truck position
```bash
mosquitto_pub -h localhost -p 1883 \
  -t "smwcs/trucks/<truck_id>/position" \
  -m '{
    "lat":       -1.2700,
    "lon":        36.8100,
    "speed_kmh":  35.5,
    "heading":    270,
    "load_kg":    450,
    "fuel_pct":   78.5
  }'
```

### Subscribe to all SMWCS topics (monitoring)
```bash
mosquitto_sub -h localhost -p 1883 -t "smwcs/#" -v
```
