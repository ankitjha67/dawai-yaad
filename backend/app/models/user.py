"""User model — supports Patient, Caregiver, Nurse, Doctor, Admin roles."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base

import enum


class UserRole(str, enum.Enum):
    patient = "patient"
    caregiver = "caregiver"
    nurse = "nurse"
    doctor = "doctor"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone = Column(String(15), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True)
    name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.patient, nullable=False)
    avatar_url = Column(Text, nullable=True)
    fcm_token = Column(Text, nullable=True)
    language = Column(String(5), default="en")
    timezone = Column(String(50), default="Asia/Kolkata")
    privacy_mode = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    medications = relationship("Medication", back_populates="user", foreign_keys="Medication.user_id")
    measurements = relationship("Measurement", back_populates="user", foreign_keys="Measurement.user_id")
    mood_logs = relationship("MoodLog", back_populates="user")
    symptom_logs = relationship("SymptomLog", back_populates="user")
    documents = relationship("Document", back_populates="user", foreign_keys="Document.user_id")
    sos_alerts = relationship("SOSAlert", back_populates="user", foreign_keys="SOSAlert.user_id")

    def __repr__(self):
        return f"<User {self.name} ({self.role.value})>"
