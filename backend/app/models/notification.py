"""Notification model — logs all push notifications sent."""

import uuid
import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class NotifType(str, enum.Enum):
    reminder = "reminder"
    missed_dose = "missed_dose"
    refill = "refill"
    sos = "sos"
    family_alert = "family_alert"
    report = "report"
    system = "system"


class NotifStatus(str, enum.Enum):
    sent = "sent"
    delivered = "delivered"
    read = "read"
    failed = "failed"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    type = Column(Enum(NotifType), nullable=False)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=True)
    medication_id = Column(UUID(as_uuid=True), ForeignKey("medications.id"), nullable=True)
    status = Column(Enum(NotifStatus), default=NotifStatus.sent)
    sent_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)
