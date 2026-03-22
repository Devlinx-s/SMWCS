import psycopg2
import structlog
from app.celery_app import celery_app
from app.config import get_settings

settings = get_settings()
log      = structlog.get_logger()


@celery_app.task(
    name='app.tasks.reports.generate_weekly_report',
    bind=True,
    max_retries=3,
)
def generate_weekly_report(self):
    """
    Generate weekly zone collection report.
    Runs every Monday at 06:00 Nairobi time.
    """
    log.info('analytics.weekly_report.starting')
    conn   = psycopg2.connect(settings.postgres_dsn_sync)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analytics_zone_weekly (
                id              SERIAL PRIMARY KEY,
                zone_id         UUID NOT NULL,
                zone_name       VARCHAR(100),
                week_start      DATE NOT NULL,
                week_end        DATE NOT NULL,
                total_shifts    INTEGER DEFAULT 0,
                total_routes    INTEGER DEFAULT 0,
                stops_planned   INTEGER DEFAULT 0,
                stops_completed INTEGER DEFAULT 0,
                completion_pct  NUMERIC(5,2) DEFAULT 0,
                active_trucks   INTEGER DEFAULT 0,
                recorded_at     TIMESTAMPTZ DEFAULT now()
            )
        """)

        cursor.execute("""
            SELECT
                z.id,
                z.name,
                DATE_TRUNC('week', now())::date - 7 AS week_start,
                DATE_TRUNC('week', now())::date - 1 AS week_end,
                COUNT(DISTINCT s.id)                 AS shifts,
                COUNT(DISTINCT r.id)                 AS routes,
                COALESCE(SUM(r.total_stops), 0)      AS stops_planned,
                COALESCE(SUM(r.stops_done), 0)       AS stops_done,
                COALESCE(ROUND(
                    SUM(r.stops_done)::numeric /
                    NULLIF(SUM(r.total_stops), 0) * 100, 2
                ), 0)                                AS completion_pct,
                COUNT(DISTINCT s.truck_id)           AS active_trucks
            FROM zones z
            LEFT JOIN bins b ON b.zone_id = z.id
            LEFT JOIN routes r ON r.zone_id::uuid = z.id
                AND r.generated_at >= DATE_TRUNC('week', now()) - INTERVAL '7 days'
                AND r.generated_at <  DATE_TRUNC('week', now())
            LEFT JOIN shifts s ON s.truck_id = r.truck_id
                AND s.status = 'completed'
                AND s.actual_start >= DATE_TRUNC('week', now()) - INTERVAL '7 days'
            GROUP BY z.id, z.name
        """)
        rows = cursor.fetchall()

        for row in rows:
            cursor.execute("""
                INSERT INTO analytics_zone_weekly
                  (zone_id, zone_name, week_start, week_end,
                   total_shifts, total_routes, stops_planned,
                   stops_completed, completion_pct, active_trucks)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, row)

        conn.commit()
        log.info('analytics.weekly_report.done', zones=len(rows))
        return {'status': 'ok', 'zones': len(rows)}

    except Exception as e:
        conn.rollback()
        log.error('analytics.weekly_report.failed', error=str(e))
        raise self.retry(exc=e, countdown=60)
    finally:
        cursor.close()
        conn.close()
