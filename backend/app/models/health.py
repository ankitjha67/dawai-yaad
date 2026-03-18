"""Health tracking models — BP, sugar, weight, mood, symptoms."""

import uuid
import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class MeasurementType(str, enum.Enum):
    bp = "bp"
    sugar = "sugar"
    weight = "weight"
    temperature = "temperature"
    pulse = "pulse"
    spo2 = "spo2"


class MoodLevel(str, enum.Enum):
    great = "great"
    good = "good"
    ok = "ok"
    bad = "bad"
    awful = "awful"


class Measurement(Base):
    __tablename__ = "measurements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    type = Column(Enum(MeasurementType), nullable=False)
    value1 = Column(Numeric(10, 2), nullable=False)
    value2 = Column(Numeric(10, 2), nullable=True)
    unit = Column(String(10), nullable=False)
    recorded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="measurements", foreign_keys=[user_id])
    recorder = relationship("User", foreign_keys=[recorded_by])


class MoodLog(Base):
    __tablename__ = "mood_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    mood = Column(Enum(MoodLevel), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="mood_logs")


class SymptomLog(Base):
    __tablename__ = "symptom_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    symptoms = Column(ARRAY(String), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="symptom_logs")
