"""Notification service — central dispatcher for push + DB logging."""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotifStatus, NotifType
from app.models.user import User
from app.services.fcm import send_push

logger = logging.getLogger(__name__)


async def send_notification(
    db: AsyncSession,
    user_id: UUID,
    title: str,
    body: str,
    notif_type: NotifType,
    medication_id: Optional[UUID] = None,
    critical: bool = False,
) -> Notification:
    """Send a notification: log to DB + push via FCM if token available.

    Args:
        db: Async database session.
        user_id: Target user.
        title: Notification title.
        body: Notification body.
        notif_type: Type of notification (reminder, missed_dose, etc.).
        medication_id: Optional linked medication.
        critical: If True, high-priority push (bypasses silent mode).

    Returns:
        The created Notification record.
    """
    # Fetch user for FCM token
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    # Create DB record
    notif = Notification(
        user_id=user_id,
        type=notif_type,
        title=title,
        body=body,
        medication_id=medication_id,
        status=NotifStatus.sent,
    )
    db.add(notif)
    await db.flush()

    # Push via FCM
    if user and user.fcm_token:
        data = {"type": notif_type.value, "notification_id": str(notif.id)}
        if medication_id:
            data["medication_id"] = str(medication_id)

        success = send_push(
            fcm_token=user.fcm_token,
            title=title,
            body=body,
            data=data,
            critical=critical,
        )
        if not success:
            notif.status = NotifStatus.failed
    else:
        logger.debug(f"No FCM token for user {user_id} — notification logged only")

    return notif


async def send_notification_sync_wrapper(
    user_id: str,
    title: str,
    body: str,
    notif_type_str: str,
    medication_id: Optional[str] = None,
    critical: bool = False,
) -> None:
    """Wrapper for use from Celery tasks via asyncio.run().

    Accepts string IDs (JSON-serializable) and creates its own DB session.
    """
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            await send_notification(
                db=db,
                user_id=UUID(user_id),
                title=title,
                body=body,
                notif_type=NotifType(notif_type_str),
                medication_id=UUID(medication_id) if medication_id else None,
                critical=critical,
            )
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f"Notification send failed: {e}")
            raise
