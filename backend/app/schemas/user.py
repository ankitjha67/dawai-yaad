"""User schemas."""

from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class UserOut(BaseModel):
    id: UUID
    phone: str
    email: Optional[str] = None
    name: str
    role: str
    avatar_url: Optional[str] = None
    language: str
    timezone: str
    privacy_mode: bool
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    privacy_mode: Optional[bool] = None
