"""Auth API — Phone OTP registration & login, JWT tokens."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.auth import (
    FCMTokenUpdate, OTPVerify, PhoneRequest,
    TokenRefresh, TokenResponse,
)
from app.utils.auth import (
    create_access_token, create_refresh_token,
    decode_token, generate_otp, get_current_user, verify_otp,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/send-otp", summary="Send OTP to phone number")
async def send_otp(req: PhoneRequest):
    """Generate and send OTP. In production, sends via MSG91/Twilio."""
    otp = generate_otp(req.phone)
    # TODO: Send OTP via MSG91 API
    # For development, return OTP in response
    return {"message": "OTP sent", "phone": req.phone, "dev_otp": otp}


@router.post("/verify-otp", response_model=TokenResponse, summary="Verify OTP & get tokens")
async def verify_otp_endpoint(req: OTPVerify, db: AsyncSession = Depends(get_db)):
    """Verify OTP. Creates user if new, returns JWT tokens."""
    if not verify_otp(req.phone, req.otp):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    # Check if user exists
    result = await db.execute(select(User).where(User.phone == req.phone))
    user = result.scalar_one_or_none()
    is_new = False

    if not user:
        # First time — require name
        if not req.name:
            raise HTTPException(status_code=400, detail="Name required for new registration")
        user = User(
            phone=req.phone,
            name=req.name,
            role=UserRole.patient,
            fcm_token=req.fcm_token,
        )
        db.add(user)
        await db.flush()
        is_new = True
    else:
        # Update FCM token on login
        if req.fcm_token:
            user.fcm_token = req.fcm_token

    access = create_access_token(str(user.id), user.role.value)
    refresh = create_refresh_token(str(user.id))

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user_id=user.id,
        role=user.role.value,
        name=user.name,
        is_new_user=is_new,
    )


@router.post("/refresh", response_model=TokenResponse, summary="Refresh access token")
async def refresh_token(req: TokenRefresh, db: AsyncSession = Depends(get_db)):
    """Exchange refresh token for new access + refresh tokens."""
    payload = decode_token(req.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=400, detail="Invalid refresh token")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")

    access = create_access_token(str(user.id), user.role.value)
    refresh = create_refresh_token(str(user.id))

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user_id=user.id,
        role=user.role.value,
        name=user.name,
    )


@router.put("/fcm-token", summary="Update FCM push token")
async def update_fcm(
    req: FCMTokenUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update Firebase Cloud Messaging token for push notifications."""
    current_user.fcm_token = req.fcm_token
    return {"message": "FCM token updated"}


@router.get("/me", summary="Get current user profile")
async def get_me(current_user: User = Depends(get_current_user)):
    """Return current authenticated user."""
    return {
        "id": str(current_user.id),
        "phone": current_user.phone,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role.value,
        "language": current_user.language,
        "timezone": current_user.timezone,
        "privacy_mode": current_user.privacy_mode,
    }
