"""Document model — blood reports, prescriptions, X-rays, etc."""

import uuid
import enum
from datetime import datetime, date

from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class DocType(str, enum.Enum):
    blood_report = "blood_report"
    prescription = "prescription"
    xray = "xray"
    scan = "scan"
    discharge_summary = "discharge_summary"
    other = "other"


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    type = Column(Enum(DocType), nullable=False, default=DocType.other)
    title = Column(String(255), nullable=False)
    file_url = Column(Text, nullable=False)
    file_size = Column(Integer, nullable=True)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    notes = Column(Text, nullable=True)
    report_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="documents", foreign_keys=[user_id])
    uploader = relationship("User", foreign_keys=[uploaded_by])
