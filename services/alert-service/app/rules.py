from app.models import AlertType, AlertSeverity


def evaluate_sensor_reading(event: dict) -> list[dict]:
    alerts = []
    sensor_id = event.get('sensor_id', 'unknown')
    fill_pct  = event.get('fill_pct', 0)
    temp_c    = event.get('temp_c', 25)
    battery   = event.get('battery_pct', 100)
    zone_id   = event.get('zone_id', 'unknown')

    if fill_pct >= 95:
        alerts.append({
            'type':      AlertType.bin_overflow,
            'severity':  AlertSeverity.critical,
            'sensor_id': sensor_id,
            'zone_id':   zone_id,
            'message':   f'CRITICAL: Bin {sensor_id} at {fill_pct:.1f}% — immediate collection required',
            'alert_metadata':  {'fill_pct': fill_pct},
        })
    elif fill_pct >= 80:
        alerts.append({
            'type':      AlertType.bin_overflow,
            'severity':  AlertSeverity.high,
            'sensor_id': sensor_id,
            'zone_id':   zone_id,
            'message':   f'Bin {sensor_id} at {fill_pct:.1f}% — collection needed soon',
            'alert_metadata':  {'fill_pct': fill_pct},
        })

    if temp_c >= 60:
        alerts.append({
            'type':      AlertType.bin_fire,
            'severity':  AlertSeverity.critical,
            'sensor_id': sensor_id,
            'zone_id':   zone_id,
            'message':   f'FIRE ALERT: Bin {sensor_id} temperature {temp_c}°C',
            'alert_metadata':  {'temp_c': temp_c},
        })

    if battery < 15:
        alerts.append({
            'type':      AlertType.sensor_low_battery,
            'severity':  AlertSeverity.low,
            'sensor_id': sensor_id,
            'zone_id':   zone_id,
            'message':   f'Sensor {sensor_id} battery at {battery}%',
            'alert_metadata':  {'battery_pct': battery},
        })

    return alerts


def evaluate_truck_telemetry(event: dict) -> list[dict]:
    alerts   = []
    truck_id = event.get('truck_id', 'unknown')
    load_kg  = event.get('load_kg', 0)
    capacity = event.get('capacity_kg', 3000)

    if load_kg > capacity * 0.95:
        alerts.append({
            'type':     AlertType.truck_overload,
            'severity': AlertSeverity.high,
            'truck_id': truck_id,
            'message':  f'Truck {truck_id} overloaded: {load_kg}kg (capacity {capacity}kg)',
            'alert_metadata': {'load_kg': load_kg, 'capacity_kg': capacity},
        })

    return alerts
