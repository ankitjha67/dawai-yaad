"""Hospital, staff, and patient assignment schemas."""

from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime


# ── Hospital ─────────────────────────────────────────────────

class HospitalCreate(BaseModel):
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None


class HospitalUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None


class HospitalOut(BaseModel):
    id: UUID
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Staff ────────────────────────────────────────────────────

class StaffAdd(BaseModel):
    phone: str  # Look up user by phone
    department: Optional[str] = None
    employee_id: Optional[str] = None
    shift: Optional[str] = None  # morning, evening, night


class StaffUpdate(BaseModel):
    department: Optional[str] = None
    employee_id: Optional[str] = None
    shift: Optional[str] = None
    is_active: Optional[bool] = None


class StaffOut(BaseModel):
    id: UUID
    hospital_id: UUID
    user_id: UUID
    user_name: Optional[str] = None
    user_phone: Optional[str] = None
    user_role: Optional[str] = None
    department: Optional[str] = None
    employee_id: Optional[str] = None
    shift: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Patient Assignment ───────────────────────────────────────

class AssignmentCreate(BaseModel):
    patient_phone: str  # Look up patient by phone
    nurse_id: UUID
    ward: Optional[str] = None
    bed_number: Optional[str] = None
    admitted_date: Optional[date] = None


class AssignmentUpdate(BaseModel):
    nurse_id: Optional[UUID] = None
    ward: Optional[str] = None
    bed_number: Optional[str] = None
    discharged_date: Optional[date] = None
    is_active: Optional[bool] = None


class AssignmentOut(BaseModel):
    id: UUID
    hospital_id: UUID
    nurse_id: UUID
    nurse_name: Optional[str] = None
    patient_id: UUID
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    ward: Optional[str] = None
    bed_number: Optional[str] = None
    admitted_date: Optional[date] = None
    discharged_date: Optional[date] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Nurse Dashboard ──────────────────────────────────────────

class NursePatientSchedule(BaseModel):
    """A single patient's medication schedule for the nurse dashboard."""
    patient_id: UUID
    patient_name: str
    ward: Optional[str] = None
    bed_number: Optional[str] = None
    medications: list = []  # List of TodayScheduleItem-like dicts
