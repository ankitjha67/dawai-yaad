"""Celery app — background tasks for reminders, escalation, reports."""

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "dawai_yaad",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    timezone="Asia/Kolkata",
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# ── Periodic Tasks (Celery Beat) ────────────────────────────
celery_app.conf.beat_schedule = {
    # Generate daily reminder tasks at 5:30 AM IST
    "generate-daily-reminders": {
        "task": "app.tasks.reminders.generate_daily_reminders",
        "schedule": crontab(hour=0, minute=0),  # midnight UTC = 5:30 AM IST
    },
    # Check for missed doses every 15 minutes
    "check-missed-doses": {
        "task": "app.tasks.reminders.check_missed_doses",
        "schedule": crontab(minute="*/15"),
    },
    # Low stock alerts daily at 9 AM IST
    "stock-alerts": {
        "task": "app.tasks.reminders.send_stock_alerts",
        "schedule": crontab(hour=3, minute=30),  # 3:30 UTC = 9 AM IST
    },
}

# ── Import tasks so Celery discovers them ────────────────────
# Must be after celery_app is defined (tasks reference it via decorator)
from app.tasks.reminders import (  # noqa: E402, F401
    generate_daily_reminders,
    check_missed_doses,
    send_stock_alerts,
    send_reminder,
)
