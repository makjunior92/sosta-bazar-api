from celery.schedules import crontab

beat_schedule = {
    "refresh-popular-searches": {
        "task": "worker.tasks.refresh_popular_searches",
        "schedule": crontab(minute=0, hour="*/6"),
    },
    "health-check-stores": {
        "task": "worker.tasks.health_check_stores",
        "schedule": crontab(minute="*/30"),
    },
}
