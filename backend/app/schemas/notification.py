"""Notification schemas."""

from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class NotificationOut(BaseModel):
    id: UUID
    user_id: UUID
    type: str
    title: str
    body: Optional[str] = None
    medication_id: Optional[UUID] = None
    status: str
    sent_at: datetime
    read_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
