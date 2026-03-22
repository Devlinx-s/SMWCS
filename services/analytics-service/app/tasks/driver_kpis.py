import psycopg2
import structlog
from app.celery_app import celery_app
from app.config import get_settings

settings = get_settings()
log      = structlog.get_logger()


@celery_app.task(
    name='app.tasks.driver_kpis.compute_driver_kpis',
    bind=True,
    max_retries=3,
)
def compute_driver_kpis(self):
    """
    Compute daily KPIs per driver from yesterday's shifts.
    Runs every day at 00:05 Nairobi time.
    """
    log.info('analytics.driver_kpis.starting')
    conn   = psycopg2.connect(settings.postgres_dsn_sync)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analytics_driver_daily (
                id              SERIAL PRIMARY KEY,
                driver_id       UUID NOT NULL,
                driver_name     VARCHAR(160),
                employee_id     VARCHAR(30),
                date            DATE NOT NULL,
                shifts_completed INTEGER DEFAULT 0,
                total_stops     INTEGER DEFAULT 0,
                stops_completed INTEGER DEFAULT 0,
                completion_pct  NUMERIC(5,2) DEFAULT 0,
                shift_hours     NUMERIC(5,2) DEFAULT 0,
                recorded_at     TIMESTAMPTZ DEFAULT now()
            )
        """)

        cursor.execute("""
            SELECT
                d.id,
                d.first_name || ' ' || d.last_name AS driver_name,
                d.employee_id,
                DATE(s.actual_start AT TIME ZONE 'Africa/Nairobi') AS shift_date,
                COUNT(DISTINCT s.id)                                AS shifts,
                COALESCE(SUM(r.total_stops), 0)                    AS total_stops,
                COALESCE(SUM(r.stops_done), 0)                     AS stops_done,
                COALESCE(
                    ROUND(
                        SUM(r.stops_done)::numeric /
                        NULLIF(SUM(r.total_stops), 0) * 100, 2
                    ), 0
                )                                                   AS completion_pct,
                COALESCE(
                    ROUND(
                        EXTRACT(EPOCH FROM SUM(
                            s.actual_end - s.actual_start
                        )) / 3600, 2
                    ), 0
                )                                                   AS shift_hours
            FROM drivers d
            JOIN shifts s ON s.driver_id = d.id
                AND s.status = 'completed'
                AND s.actual_start >= now() - INTERVAL '2 days'
                AND s.actual_start <  now() - INTERVAL '1 day'
            LEFT JOIN routes r ON r.truck_id = s.truck_id
                AND r.generated_at::date = s.actual_start::date
            GROUP BY d.id, d.first_name, d.last_name,
                     d.employee_id, shift_date
        """)
        rows = cursor.fetchall()

        for row in rows:
            cursor.execute("""
                INSERT INTO analytics_driver_daily
                  (driver_id, driver_name, employee_id, date,
                   shifts_completed, total_stops, stops_completed,
                   completion_pct, shift_hours)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, row)

        conn.commit()
        log.info('analytics.driver_kpis.done', drivers=len(rows))
        return {'status': 'ok', 'drivers': len(rows)}

    except Exception as e:
        conn.rollback()
        log.error('analytics.driver_kpis.failed', error=str(e))
        raise self.retry(exc=e, countdown=60)
    finally:
        cursor.close()
        conn.close()
