"""Medication & DoseLog schemas."""

from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime, time


class MedicationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    category: str = "medicine"
    form: str = "tablet"
    dose_amount: Optional[str] = None
    dose_unit: Optional[str] = None
    meal_slot: Optional[str] = None
    exact_hour: Optional[int] = Field(None, ge=0, le=23)
    exact_minute: Optional[int] = Field(None, ge=0, le=59)
    frequency: str = "daily"
    freq_custom_days: Optional[List[int]] = None
    freq_weekly_day: Optional[int] = Field(None, ge=0, le=6)
    freq_monthly_day: Optional[int] = Field(None, ge=1, le=28)
    freq_hourly_interval: Optional[int] = Field(None, ge=1, le=24)
    freq_hourly_from: Optional[int] = Field(None, ge=0, le=23)
    freq_hourly_to: Optional[int] = Field(None, ge=0, le=23)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    body_area: Optional[str] = None
    stock_quantity: int = 0
    stock_unit: Optional[str] = None
    stock_alert_threshold: int = 5
    color: str = "#059669"
    is_private: bool = True
    notes: Optional[str] = None


class MedicationUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    form: Optional[str] = None
    dose_amount: Optional[str] = None
    dose_unit: Optional[str] = None
    meal_slot: Optional[str] = None
    exact_hour: Optional[int] = None
    exact_minute: Optional[int] = None
    frequency: Optional[str] = None
    freq_custom_days: Optional[List[int]] = None
    freq_weekly_day: Optional[int] = None
    freq_monthly_day: Optional[int] = None
    freq_hourly_interval: Optional[int] = None
    freq_hourly_from: Optional[int] = None
    freq_hourly_to: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    body_area: Optional[str] = None
    stock_quantity: Optional[int] = None
    stock_unit: Optional[str] = None
    stock_alert_threshold: Optional[int] = None
    color: Optional[str] = None
    is_private: Optional[bool] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class MedicationOut(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    category: str
    form: str
    dose_amount: Optional[str] = None
    dose_unit: Optional[str] = None
    meal_slot: Optional[str] = None
    exact_hour: Optional[int] = None
    exact_minute: Optional[int] = None
    frequency: str
    freq_custom_days: Optional[List[int]] = None
    freq_weekly_day: Optional[int] = None
    freq_monthly_day: Optional[int] = None
    freq_hourly_interval: Optional[int] = None
    freq_hourly_from: Optional[int] = None
    freq_hourly_to: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    body_area: Optional[str] = None
    injection_site_index: int = 0
    stock_quantity: int = 0
    stock_unit: Optional[str] = None
    stock_alert_threshold: int = 5
    color: str
    is_private: bool
    notes: Optional[str] = None
    is_active: bool
    created_by: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class DoseLogCreate(BaseModel):
    status: str = "taken"  # taken, skipped, snoozed
    notes: Optional[str] = None


class DoseLogOut(BaseModel):
    id: UUID
    medication_id: UUID
    user_id: UUID
    scheduled_date: date
    scheduled_time: Optional[time] = None
    status: str
    actual_time: Optional[datetime] = None
    logged_by: UUID
    injection_site: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TodayScheduleItem(BaseModel):
    medication: MedicationOut
    dose_log: Optional[DoseLogOut] = None
    is_due: bool = False
    is_missed: bool = False
