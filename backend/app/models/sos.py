"""SOS Alert model."""

import uuid
import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class SOSStatus(str, enum.Enum):
    triggered = "triggered"
    acknowledged = "acknowledged"
    resolved = "resolved"


class SOSAlert(Base):
    __tablename__ = "sos_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    status = Column(Enum(SOSStatus), default=SOSStatus.triggered, nullable=False)
    triggered_at = Column(DateTime, default=datetime.utcnow)
    acknowledged_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    location_lat = Column(Numeric(10, 7), nullable=True)
    location_lng = Column(Numeric(10, 7), nullable=True)

    user = relationship("User", back_populates="sos_alerts", foreign_keys=[user_id])
    acknowledger = relationship("User", foreign_keys=[acknowledged_by])
