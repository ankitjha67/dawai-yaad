"""Health measurement, mood, symptom, and SOS schemas."""

from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


# ── Measurements ─────────────────────────────────
class MeasurementCreate(BaseModel):
    type: str  # bp, sugar, weight, temperature, pulse, spo2
    value1: float
    value2: Optional[float] = None
    unit: str
    notes: Optional[str] = None


class MeasurementOut(BaseModel):
    id: UUID
    user_id: UUID
    type: str
    value1: float
    value2: Optional[float] = None
    unit: str
    recorded_by: UUID
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Mood ─────────────────────────────────────────
class MoodCreate(BaseModel):
    mood: str  # great, good, ok, bad, awful
    notes: Optional[str] = None


class MoodOut(BaseModel):
    id: UUID
    user_id: UUID
    mood: str
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Symptoms ─────────────────────────────────────
class SymptomCreate(BaseModel):
    symptoms: List[str]
    notes: Optional[str] = None


class SymptomOut(BaseModel):
    id: UUID
    user_id: UUID
    symptoms: List[str]
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── SOS ──────────────────────────────────────────
class SOSTrigger(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    notes: Optional[str] = None


class SOSAcknowledge(BaseModel):
    notes: Optional[str] = None


class SOSOut(BaseModel):
    id: UUID
    user_id: UUID
    status: str
    triggered_at: datetime
    acknowledged_by: Optional[UUID] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    notes: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None

    model_config = {"from_attributes": True}
