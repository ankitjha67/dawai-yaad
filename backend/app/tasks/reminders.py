"""Celery reminder tasks — daily generation, escalation, stock alerts.

Escalation chain (from PROJECT-PLAN.md):
    T+0  min → Push notification to patient
    T+5  min → Second push (CRITICAL — bypasses silent mode)
    T+15 min → Alert ALL caregivers via push
    T+30 min → WhatsApp to patient + caregivers (TODO: Session 6)
    T+60 min → Mark MISSED, full family alert, nurse if hospitalized
"""

import logging
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import and_, select

from app.database import SyncSessionLocal
from app.models.family import FamilyMember
from app.models.hospital import PatientAssignment
from app.models.medication import DoseLog, DoseStatus, Medication, MedFrequency
from app.models.notification import Notification, NotifStatus, NotifType
from app.models.user import User
from app.services.fcm import send_push, send_push_to_many
from app.tasks import celery_app

logger = logging.getLogger(__name__)


# ── Schedule helper (sync version, mirrors api/medications.py) ──

def _is_due_on(med: Medication, check_date: date) -> bool:
    """Check if a medication is due on a given date."""
    freq = med.frequency.value if med.frequency else "daily"
    if freq == "as_needed":
        return False

    start = med.start_date or check_date
    if check_date < start:
        return False
    if med.end_date and check_date > med.end_date:
        return False

    diff_days = (check_date - start).days
    diff_months = (check_date.year - start.year) * 12 + check_date.month - start.month

    if freq in ("daily", "hourly"):
        return True
    elif freq == "alternate":
        return diff_days % 2 == 0
    elif freq == "custom_days":
        return check_date.weekday() in (med.freq_custom_days or [])
    elif freq == "weekly":
        py_day = (check_date.weekday() + 1) % 7
        return py_day == (med.freq_weekly_day if med.freq_weekly_day is not None else start.weekday())
    elif freq == "biweekly":
        py_day = (check_date.weekday() + 1) % 7
        return py_day == (med.freq_weekly_day or 0) and (diff_days // 7) % 2 == 0
    elif freq == "monthly":
        return check_date.day == (med.freq_monthly_day or start.day)
    elif freq == "quarterly":
        return check_date.day == (med.freq_monthly_day or start.day) and diff_months >= 0 and diff_months % 3 == 0
    elif freq == "half_yearly":
        return check_date.day == (med.freq_monthly_day or start.day) and diff_months >= 0 and diff_months % 6 == 0
    elif freq == "yearly":
        return check_date.day == start.day and check_date.month == start.month

    return True


def _get_scheduled_times(med: Medication) -> list[time]:
    """Get all scheduled times for a medication on a given day.

    For hourly medications, expands the interval range into individual times.
    For all others, returns the single exact_hour/exact_minute time.
    """
    freq = med.frequency.value if med.frequency else "daily"

    if freq == "hourly" and med.freq_hourly_interval and med.freq_hourly_from is not None:
        times = []
        hour = med.freq_hourly_from
        end_hour = med.freq_hourly_to or 23
        while hour <= end_hour:
            times.append(time(hour, med.exact_minute or 0))
            hour += med.freq_hourly_interval
        return times

    if med.exact_hour is not None:
        return [time(med.exact_hour, med.exact_minute or 0)]

    return []


# ── Celery Tasks ─────────────────────────────────────────────

@celery_app.task(name="app.tasks.reminders.generate_daily_reminders")
def generate_daily_reminders():
    """Generate individual reminder tasks for all users' medications today.

    Runs at midnight UTC (5:30 AM IST) via Celery Beat.
    For each active medication due today, schedules a send_reminder task
    at the medication's scheduled time.
    """
    today = date.today()
    now = datetime.now(timezone.utc)
    scheduled_count = 0

    with SyncSessionLocal() as db:
        # Get all active medications
        meds = db.execute(
            select(Medication).where(Medication.is_active == True)
        ).scalars().all()

        for med in meds:
            if not _is_due_on(med, today):
                continue

            scheduled_times = _get_scheduled_times(med)
            for sched_time in scheduled_times:
                # Calculate ETA for this reminder
                sched_dt = datetime.combine(today, sched_time, tzinfo=timezone.utc)

                if sched_dt <= now:
                    # Already past — skip (check_missed_doses will handle it)
                    continue

                # Schedule the reminder at the exact time
                delay_seconds = (sched_dt - now).total_seconds()
                send_reminder.apply_async(
                    args=[str(med.user_id), str(med.id), 0],
                    countdown=delay_seconds,
                )
                scheduled_count += 1

    logger.info(f"Generated {scheduled_count} reminder tasks for {today}")
    return {"date": str(today), "reminders_scheduled": scheduled_count}


@celery_app.task(name="app.tasks.reminders.check_missed_doses")
def check_missed_doses():
    """Check for doses past their time without a log. Trigger escalation.

    Runs every 15 minutes via Celery Beat.
    Finds medications whose scheduled time was 60+ minutes ago with no dose_log,
    marks them missed, and sends family alerts.
    """
    today = date.today()
    now = datetime.now(timezone.utc)
    missed_count = 0

    with SyncSessionLocal() as db:
        # Get all active medications
        meds = db.execute(
            select(Medication).where(Medication.is_active == True)
        ).scalars().all()

        for med in meds:
            if not _is_due_on(med, today):
                continue

            for sched_time in _get_scheduled_times(med):
                sched_dt = datetime.combine(today, sched_time, tzinfo=timezone.utc)

                # Only check doses that are 60+ minutes overdue
                if now < sched_dt + timedelta(minutes=60):
                    continue

                # Check if already logged
                existing = db.execute(
                    select(DoseLog).where(
                        and_(
                            DoseLog.medication_id == med.id,
                            DoseLog.scheduled_date == today,
                            DoseLog.status.in_([DoseStatus.taken, DoseStatus.skipped, DoseStatus.missed]),
                        )
                    )
                ).scalar_one_or_none()

                if existing:
                    continue

                # Mark as missed
                dose_log = DoseLog(
                    medication_id=med.id,
                    user_id=med.user_id,
                    scheduled_date=today,
                    scheduled_time=sched_time,
                    status=DoseStatus.missed,
                    logged_by=med.user_id,
                )
                db.add(dose_log)

                # Log notification for patient
                notif = Notification(
                    user_id=med.user_id,
                    type=NotifType.missed_dose,
                    title=f"Missed: {med.name}",
                    body=f"You missed {med.name} scheduled at {sched_time.strftime('%I:%M %p')}",
                    medication_id=med.id,
                    status=NotifStatus.sent,
                )
                db.add(notif)

                # Push to patient
                user = db.execute(
                    select(User).where(User.id == med.user_id)
                ).scalar_one_or_none()

                if user and user.fcm_token:
                    send_push(
                        fcm_token=user.fcm_token,
                        title=notif.title,
                        body=notif.body,
                        data={"type": "missed_dose", "medication_id": str(med.id)},
                        critical=True,
                    )

                # Alert family caregivers who receive missed alerts
                _alert_family_missed(db, med, user, sched_time)

                # Alert nurse if hospitalized
                _alert_nurse_missed(db, med, sched_time)

                missed_count += 1

        db.commit()

    logger.info(f"Found {missed_count} missed doses")
    return {"missed_count": missed_count}


@celery_app.task(name="app.tasks.reminders.send_stock_alerts")
def send_stock_alerts():
    """Send push notifications for low-stock medications.

    Runs daily at 9 AM IST via Celery Beat.
    """
    alert_count = 0

    with SyncSessionLocal() as db:
        # Find low-stock medications
        low_stock_meds = db.execute(
            select(Medication).where(
                and_(
                    Medication.is_active == True,
                    Medication.stock_quantity > 0,
                    Medication.stock_quantity <= Medication.stock_alert_threshold,
                )
            )
        ).scalars().all()

        for med in low_stock_meds:
            user = db.execute(
                select(User).where(User.id == med.user_id)
            ).scalar_one_or_none()

            if not user:
                continue

            title = f"Low stock: {med.name}"
            body = f"Only {med.stock_quantity} {med.stock_unit or 'doses'} remaining. Time to refill!"

            notif = Notification(
                user_id=med.user_id,
                type=NotifType.refill,
                title=title,
                body=body,
                medication_id=med.id,
                status=NotifStatus.sent,
            )
            db.add(notif)

            if user.fcm_token:
                send_push(
                    fcm_token=user.fcm_token,
                    title=title,
                    body=body,
                    data={"type": "refill", "medication_id": str(med.id)},
                )

            alert_count += 1

        db.commit()

    logger.info(f"Sent {alert_count} stock alerts")
    return {"stock_alerts_sent": alert_count}


@celery_app.task(
    name="app.tasks.reminders.send_reminder",
    bind=True,
    max_retries=0,
)
def send_reminder(self, user_id: str, medication_id: str, escalation_level: int = 0):
    """Send a medication reminder with escalation chain.

    Escalation levels:
        0 — T+0:  Normal push to patient
        1 — T+5:  CRITICAL push to patient (bypasses silent mode)
        2 — T+15: Alert ALL caregivers via push
        3 — T+30: (Reserved for WhatsApp — TODO Session 6)
        4 — T+60: Mark MISSED, full family + nurse alert (handled by check_missed_doses)
    """
    with SyncSessionLocal() as db:
        med = db.execute(
            select(Medication).where(Medication.id == medication_id)
        ).scalar_one_or_none()

        if not med or not med.is_active:
            return {"status": "skipped", "reason": "medication not found or inactive"}

        # Check if already taken/skipped today
        today = date.today()
        existing = db.execute(
            select(DoseLog).where(
                and_(
                    DoseLog.medication_id == med.id,
                    DoseLog.scheduled_date == today,
                    DoseLog.status.in_([DoseStatus.taken, DoseStatus.skipped]),
                )
            )
        ).scalar_one_or_none()

        if existing:
            return {"status": "skipped", "reason": "dose already logged"}

        user = db.execute(
            select(User).where(User.id == user_id)
        ).scalar_one_or_none()

        if not user:
            return {"status": "skipped", "reason": "user not found"}

        time_str = ""
        if med.exact_hour is not None:
            time_str = f" at {time(med.exact_hour, med.exact_minute or 0).strftime('%I:%M %p')}"

        # ── Escalation Level 0: Normal push to patient ──
        if escalation_level == 0:
            title = f"Time for {med.name}"
            body = f"Take {med.dose_amount or ''} {med.dose_unit or ''} of {med.name}{time_str}"

            notif = Notification(
                user_id=user.id,
                type=NotifType.reminder,
                title=title,
                body=body.strip(),
                medication_id=med.id,
                status=NotifStatus.sent,
            )
            db.add(notif)

            if user.fcm_token:
                send_push(
                    fcm_token=user.fcm_token,
                    title=title,
                    body=body.strip(),
                    data={"type": "reminder", "medication_id": str(med.id), "escalation": "0"},
                )

            # Schedule next escalation in 5 minutes
            send_reminder.apply_async(
                args=[user_id, medication_id, 1],
                countdown=300,  # 5 minutes
            )

        # ── Escalation Level 1: CRITICAL push to patient ──
        elif escalation_level == 1:
            title = f"REMINDER: {med.name}"
            body = f"You haven't taken {med.name}{time_str}. Please take it now."

            notif = Notification(
                user_id=user.id,
                type=NotifType.reminder,
                title=title,
                body=body,
                medication_id=med.id,
                status=NotifStatus.sent,
            )
            db.add(notif)

            if user.fcm_token:
                send_push(
                    fcm_token=user.fcm_token,
                    title=title,
                    body=body,
                    data={"type": "reminder", "medication_id": str(med.id), "escalation": "1"},
                    critical=True,
                )

            # Schedule caregiver alert in 10 minutes (T+15 total)
            send_reminder.apply_async(
                args=[user_id, medication_id, 2],
                countdown=600,  # 10 minutes
            )

        # ── Escalation Level 2: Alert ALL caregivers ──
        elif escalation_level == 2:
            # Get family members who receive missed alerts
            caregiver_tokens = _get_caregiver_fcm_tokens(db, user.id)

            if caregiver_tokens:
                title = f"{user.name} hasn't taken {med.name}"
                body = f"{user.name} missed {med.name}{time_str}. Please check on them."

                send_push_to_many(
                    fcm_tokens=caregiver_tokens,
                    title=title,
                    body=body,
                    data={"type": "family_alert", "medication_id": str(med.id), "patient_id": str(user.id)},
                    critical=True,
                )

                # Log notification for each caregiver
                caregiver_ids = _get_caregiver_user_ids(db, user.id)
                for cg_id in caregiver_ids:
                    notif = Notification(
                        user_id=cg_id,
                        type=NotifType.family_alert,
                        title=title,
                        body=body,
                        medication_id=med.id,
                        status=NotifStatus.sent,
                    )
                    db.add(notif)

            # Escalation Level 3 (WhatsApp) reserved for Session 6
            # Level 4 (mark missed) handled by check_missed_doses periodic task

        db.commit()

    return {
        "status": "sent",
        "escalation_level": escalation_level,
        "medication": medication_id,
    }


# ── Helper functions ─────────────────────────────────────────

def _get_caregiver_fcm_tokens(db, patient_user_id) -> list[str]:
    """Get FCM tokens of caregivers who receive missed alerts for a patient."""
    # Find families the patient belongs to
    patient_families = select(FamilyMember.family_id).where(
        FamilyMember.user_id == patient_user_id
    ).scalar_subquery()

    # Get members with receives_missed_alerts=True
    members = db.execute(
        select(FamilyMember).where(
            and_(
                FamilyMember.family_id.in_(patient_families),
                FamilyMember.user_id != patient_user_id,
                FamilyMember.receives_missed_alerts == True,
            )
        )
    ).scalars().all()

    tokens = []
    for m in members:
        user = db.execute(
            select(User).where(User.id == m.user_id)
        ).scalar_one_or_none()
        if user and user.fcm_token:
            tokens.append(user.fcm_token)

    return tokens


def _get_caregiver_user_ids(db, patient_user_id) -> list:
    """Get user_ids of caregivers who receive missed alerts."""
    patient_families = select(FamilyMember.family_id).where(
        FamilyMember.user_id == patient_user_id
    ).scalar_subquery()

    members = db.execute(
        select(FamilyMember.user_id).where(
            and_(
                FamilyMember.family_id.in_(patient_families),
                FamilyMember.user_id != patient_user_id,
                FamilyMember.receives_missed_alerts == True,
            )
        ).distinct()
    ).all()

    return [row[0] for row in members]


def _alert_family_missed(db, med: Medication, user: User, sched_time: time):
    """Send missed-dose alerts to family caregivers."""
    caregiver_tokens = _get_caregiver_fcm_tokens(db, med.user_id)
    if not caregiver_tokens:
        return

    patient_name = user.name if user else "Patient"
    title = f"Missed: {patient_name} — {med.name}"
    body = f"{patient_name} missed {med.name} scheduled at {sched_time.strftime('%I:%M %p')}"

    send_push_to_many(
        fcm_tokens=caregiver_tokens,
        title=title,
        body=body,
        data={"type": "missed_dose", "medication_id": str(med.id), "patient_id": str(med.user_id)},
        critical=True,
    )

    # Log notifications
    for cg_id in _get_caregiver_user_ids(db, med.user_id):
        notif = Notification(
            user_id=cg_id,
            type=NotifType.family_alert,
            title=title,
            body=body,
            medication_id=med.id,
            status=NotifStatus.sent,
        )
        db.add(notif)


def _alert_nurse_missed(db, med: Medication, sched_time: time):
    """Alert assigned nurses if patient is hospitalized."""
    # Find active nurse assignments for this patient
    assignments = db.execute(
        select(PatientAssignment).where(
            and_(
                PatientAssignment.patient_id == med.user_id,
                PatientAssignment.is_active == True,
            )
        )
    ).scalars().all()

    for assignment in assignments:
        nurse = db.execute(
            select(User).where(User.id == assignment.nurse_id)
        ).scalar_one_or_none()

        if not nurse:
            continue

        title = f"Patient missed: {med.name}"
        body = (
            f"Ward {assignment.ward or '?'} / Bed {assignment.bed_number or '?'} — "
            f"Missed {med.name} at {sched_time.strftime('%I:%M %p')}"
        )

        notif = Notification(
            user_id=nurse.id,
            type=NotifType.missed_dose,
            title=title,
            body=body,
            medication_id=med.id,
            status=NotifStatus.sent,
        )
        db.add(notif)

        if nurse.fcm_token:
            send_push(
                fcm_token=nurse.fcm_token,
                title=title,
                body=body,
                data={"type": "missed_dose", "medication_id": str(med.id)},
                critical=True,
            )
