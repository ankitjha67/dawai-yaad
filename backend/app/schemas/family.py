"""Family schemas."""

from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class FamilyCreate(BaseModel):
    name: str


class FamilyMemberAdd(BaseModel):
    phone: str  # Phone number of existing user OR invite
    relationship: str
    nickname: Optional[str] = None
    can_edit: bool = False
    receives_sos: bool = True
    receives_missed_alerts: bool = True


class FamilyMemberUpdate(BaseModel):
    relationship: Optional[str] = None
    nickname: Optional[str] = None
    can_edit: Optional[bool] = None
    receives_sos: Optional[bool] = None
    receives_missed_alerts: Optional[bool] = None


class FamilyMemberOut(BaseModel):
    id: UUID
    user_id: UUID
    user_name: Optional[str] = None
    user_phone: Optional[str] = None
    relationship: str
    nickname: Optional[str] = None
    can_edit: bool
    receives_sos: bool
    receives_missed_alerts: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class FamilyOut(BaseModel):
    id: UUID
    name: str
    created_by: UUID
    members: List[FamilyMemberOut] = []
    created_at: datetime

    model_config = {"from_attributes": True}
