"""Auth schemas — registration, login, tokens."""

from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID


class PhoneRequest(BaseModel):
    phone: str = Field(..., pattern=r"^\+?[1-9]\d{6,14}$", examples=["+919876543210"])


class OTPVerify(BaseModel):
    phone: str = Field(..., pattern=r"^\+?[1-9]\d{6,14}$")
    otp: str = Field(..., min_length=4, max_length=6)
    name: Optional[str] = None  # Required on first registration
    fcm_token: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: UUID
    role: str
    name: str
    is_new_user: bool = False


class TokenRefresh(BaseModel):
    refresh_token: str


class FCMTokenUpdate(BaseModel):
    fcm_token: str


class GoogleAuthRequest(BaseModel):
    id_token: str
    fcm_token: Optional[str] = None
