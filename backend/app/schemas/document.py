"""Document schemas."""

from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import date, datetime


class DocumentCreate(BaseModel):
    type: str = "other"  # blood_report, prescription, xray, scan, discharge_summary, other
    title: str
    notes: Optional[str] = None
    report_date: Optional[date] = None


class DocumentOut(BaseModel):
    id: UUID
    user_id: UUID
    type: str
    title: str
    file_url: Optional[str] = None
    file_size: Optional[int] = None
    uploaded_by: UUID
    uploaded_by_name: Optional[str] = None
    notes: Optional[str] = None
    report_date: Optional[date] = None
    created_at: datetime

    model_config = {"from_attributes": True}
