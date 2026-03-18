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


@celery_app.task(name="app.tasks.reminders.generate_daily_reminders")
def generate_daily_reminders():
    """Generate individual reminder tasks for all users' medications today."""
    # TODO: Query all active medications, check schedule, create individual tasks
    pass


@celery_app.task(name="app.tasks.reminders.check_missed_doses")
def check_missed_doses():
    """Check for doses past their time that haven't been logged. Trigger escalation."""
    # TODO: Query medications due in last hour without dose_log, send alerts
    pass


@celery_app.task(name="app.tasks.reminders.send_stock_alerts")
def send_stock_alerts():
    """Send push notifications for low-stock medications."""
    # TODO: Query medications where stock <= threshold, push to user + caregivers
    pass


@celery_app.task(name="app.tasks.reminders.send_reminder")
def send_reminder(user_id: str, medication_id: str, escalation_level: int = 0):
    """Send a single medication reminder. Escalates if not acknowledged."""
    # TODO: Send FCM push, schedule next escalation if no response
    pass


@celery_app.task(name="app.tasks.reminders.send_fcm_push")
def send_fcm_push(fcm_token: str, title: str, body: str, data: dict = None):
    """Send Firebase Cloud Messaging push notification."""
    # TODO: Use firebase_admin SDK to send push
    pass
