"""Notifications API — list, read, count unread."""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.notification import Notification, NotifStatus, NotifType
from app.models.user import User
from app.schemas.notification import NotificationOut
from app.utils.auth import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=List[NotificationOut], summary="List my notifications")
async def list_notifications(
    type: Optional[str] = None,
    unread_only: bool = False,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List notifications for the current user, newest first."""
    query = select(Notification).where(Notification.user_id == current_user.id)

    if type:
        query = query.where(Notification.type == type)
    if unread_only:
        query = query.where(Notification.read_at == None)

    query = query.order_by(Notification.sent_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/unread-count", summary="Count unread notifications")
async def unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get count of unread notifications."""
    result = await db.execute(
        select(func.count(Notification.id)).where(
            and_(
                Notification.user_id == current_user.id,
                Notification.read_at == None,
            )
        )
    )
    count = result.scalar()
    return {"unread_count": count}


@router.put("/{notif_id}/read", response_model=NotificationOut, summary="Mark as read")
async def mark_read(
    notif_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a single notification as read."""
    result = await db.execute(
        select(Notification).where(
            and_(Notification.id == notif_id, Notification.user_id == current_user.id)
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    notif.read_at = datetime.now(timezone.utc)
    notif.status = NotifStatus.read
    await db.flush()
    await db.refresh(notif)
    return notif


@router.put("/read-all", summary="Mark all notifications as read")
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all unread notifications as read for the current user."""
    now = datetime.now(timezone.utc)
    await db.execute(
        update(Notification)
        .where(
            and_(
                Notification.user_id == current_user.id,
                Notification.read_at == None,
            )
        )
        .values(read_at=now, status=NotifStatus.read)
    )
    return {"message": "All notifications marked as read"}
