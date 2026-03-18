"""Medication and DoseLog models — supports all form types, frequencies, and dose tracking."""

import uuid
import enum
from datetime import datetime, date

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Enum, ForeignKey,
    Integer, SmallInteger, String, Text, Time
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class MedCategory(str, enum.Enum):
    medicine = "medicine"
    supplement = "supplement"
    injection = "injection"
    checkup = "checkup"
    appointment = "appointment"
    measurement = "measurement"


class MedForm(str, enum.Enum):
    tablet = "tablet"
    capsule = "capsule"
    syrup = "syrup"
    drops = "drops"
    injection = "injection"
    inhaler = "inhaler"
    cream = "cream"
    powder = "powder"
    gel = "gel"
    spray = "spray"
    patch = "patch"


class MedFrequency(str, enum.Enum):
    daily = "daily"
    alternate = "alternate"
    custom_days = "custom_days"
    hourly = "hourly"
    weekly = "weekly"
    biweekly = "biweekly"
    monthly = "monthly"
    quarterly = "quarterly"
    half_yearly = "half_yearly"
    yearly = "yearly"
    as_needed = "as_needed"


class DoseStatus(str, enum.Enum):
    taken = "taken"
    skipped = "skipped"
    missed = "missed"
    snoozed = "snoozed"


class Medication(Base):
    __tablename__ = "medications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # Basic info
    name = Column(String(255), nullable=False)
    category = Column(Enum(MedCategory), nullable=False, default=MedCategory.medicine)
    form = Column(Enum(MedForm), nullable=False, default=MedForm.tablet)

    # Dosage with proper units
    dose_amount = Column(String(50), nullable=True)  # "2", "10", "500"
    dose_unit = Column(String(30), nullable=True)  # "ml", "tsp", "tablet", "mg", "puffs", "application"

    # Schedule
    meal_slot = Column(String(20), nullable=True)
    exact_hour = Column(SmallInteger, nullable=True)
    exact_minute = Column(SmallInteger, nullable=True)

    # Frequency
    frequency = Column(Enum(MedFrequency), nullable=False, default=MedFrequency.daily)
    freq_custom_days = Column(ARRAY(SmallInteger), nullable=True)  # [1,3,5] = Mon,Wed,Fri
    freq_weekly_day = Column(SmallInteger, nullable=True)
    freq_monthly_day = Column(SmallInteger, nullable=True)
    freq_hourly_interval = Column(SmallInteger, nullable=True)  # 2,3,4,6,8,12
    freq_hourly_from = Column(SmallInteger, nullable=True)  # start hour (0-23)
    freq_hourly_to = Column(SmallInteger, nullable=True)  # end hour (0-23)

    # Dates
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    # Topical/Injection specifics
    body_area = Column(String(100), nullable=True)
    injection_site_index = Column(SmallInteger, default=0)

    # Stock tracking
    stock_quantity = Column(Integer, default=0)
    stock_unit = Column(String(20), nullable=True)  # "tablet", "bottle", "tube", "strip"
    stock_alert_threshold = Column(Integer, default=5)

    # Display
    color = Column(String(7), default="#059669")
    is_private = Column(Boolean, default=True)  # Default to PRIVATE
    notes = Column(Text, nullable=True)

    # Metadata
    is_active = Column(Boolean, default=True)
    prescribed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="medications", foreign_keys=[user_id])
    prescriber = relationship("User", foreign_keys=[prescribed_by])
    creator = relationship("User", foreign_keys=[created_by])
    dose_logs = relationship("DoseLog", back_populates="medication", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Medication {self.name} ({self.frequency.value})>"


class DoseLog(Base):
    __tablename__ = "dose_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    medication_id = Column(UUID(as_uuid=True), ForeignKey("medications.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    scheduled_date = Column(Date, nullable=False)
    scheduled_time = Column(Time, nullable=True)
    status = Column(Enum(DoseStatus), nullable=False)
    actual_time = Column(DateTime, nullable=True)
    logged_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    injection_site = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    medication = relationship("Medication", back_populates="dose_logs")
    user = relationship("User", foreign_keys=[user_id])
    logger = relationship("User", foreign_keys=[logged_by])

    def __repr__(self):
        return f"<DoseLog {self.status.value} on {self.scheduled_date}>"
