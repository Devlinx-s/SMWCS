import psycopg2
import structlog
from app.celery_app import celery_app
from app.config import get_settings

settings = get_settings()
log      = structlog.get_logger()


def get_conn():
    return psycopg2.connect(settings.postgres_dsn_sync)


@celery_app.task(
    name='app.tasks.aggregation.aggregate_zone_hourly',
    bind=True,
    max_retries=3,
)
def aggregate_zone_hourly(self):
    """
    Count bins by status per zone and write to analytics_zone_hourly.
    Runs every hour.
    """
    log.info('analytics.zone_hourly.starting')
    conn   = get_conn()
    cursor = conn.cursor()

    try:
        # Create analytics table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analytics_zone_hourly (
                id           SERIAL PRIMARY KEY,
                zone_id      UUID NOT NULL,
                zone_name    VARCHAR(100),
                zone_code    VARCHAR(20),
                recorded_at  TIMESTAMPTZ DEFAULT now(),
                total_bins   INTEGER DEFAULT 0,
                active_bins  INTEGER DEFAULT 0,
                maintenance  INTEGER DEFAULT 0,
                decommissioned INTEGER DEFAULT 0
            )
        """)

        # Aggregate bins per zone
        cursor.execute("""
            SELECT
                z.id,
                z.name,
                z.code,
                COUNT(b.id)                                          AS total,
                COUNT(b.id) FILTER (WHERE b.status = 'active')       AS active,
                COUNT(b.id) FILTER (WHERE b.status = 'maintenance')  AS maintenance,
                COUNT(b.id) FILTER (WHERE b.status = 'decommissioned') AS decommissioned
            FROM zones z
            LEFT JOIN bins b ON b.zone_id = z.id
            GROUP BY z.id, z.name, z.code
        """)
        zones = cursor.fetchall()

        for zone_id, name, code, total, active, maint, decomm in zones:
            cursor.execute("""
                INSERT INTO analytics_zone_hourly
                  (zone_id, zone_name, zone_code, total_bins,
                   active_bins, maintenance, decommissioned)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (zone_id, name, code, total, active, maint, decomm))

        conn.commit()
        log.info('analytics.zone_hourly.done', zones=len(zones))
        return {'status': 'ok', 'zones': len(zones)}

    except Exception as e:
        conn.rollback()
        log.error('analytics.zone_hourly.failed', error=str(e))
        raise self.retry(exc=e, countdown=60)
    finally:
        cursor.close()
        conn.close()
