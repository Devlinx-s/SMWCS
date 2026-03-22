from celery import Celery
from celery.schedules import crontab
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    'smwcs-analytics',
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        'app.tasks.aggregation',
        'app.tasks.driver_kpis',
        'app.tasks.reports',
    ],
)

celery_app.conf.timezone           = 'Africa/Nairobi'
celery_app.conf.task_serializer    = 'json'
celery_app.conf.result_serializer  = 'json'
celery_app.conf.accept_content     = ['json']
celery_app.conf.task_track_started = True

celery_app.conf.beat_schedule = {
    'hourly-zone-aggregation': {
        'task':     'app.tasks.aggregation.aggregate_zone_hourly',
        'schedule': crontab(minute=0),
    },
    'daily-driver-kpis': {
        'task':     'app.tasks.driver_kpis.compute_driver_kpis',
        'schedule': crontab(hour=0, minute=5),
    },
    'weekly-zone-report': {
        'task':     'app.tasks.reports.generate_weekly_report',
        'schedule': crontab(day_of_week=1, hour=6, minute=0),
    },
}
