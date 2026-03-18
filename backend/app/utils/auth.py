"""Auth utilities — JWT, OTP, current user extraction."""

import random
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.user import User, UserRole

settings = get_settings()
security = HTTPBearer()

# ── In-memory OTP store (use Redis in production) ──────────
_otp_store: dict[str, dict] = {}


def generate_otp(phone: str) -> str:
    """Generate 6-digit OTP and store it."""
    otp = str(random.randint(100000, 999999))
    _otp_store[phone] = {
        "otp": otp,
        "expires": datetime.now(timezone.utc) + timedelta(minutes=10),
    }
    return otp


def verify_otp(phone: str, otp: str) -> bool:
    """Verify OTP for given phone number."""
    stored = _otp_store.get(phone)
    if not stored:
        return False
    if datetime.now(timezone.utc) > stored["expires"]:
        _otp_store.pop(phone, None)
        return False
    if stored["otp"] != otp:
        return False
    _otp_store.pop(phone, None)
    return True


def create_access_token(user_id: str, role: str) -> str:
    """Create JWT access token."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str) -> str:
    """Create JWT refresh token."""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency — extract current user from JWT."""
    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user


def require_roles(*roles: UserRole):
    """Factory for role-based access control dependency."""
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role.value}' not authorized. Required: {[r.value for r in roles]}",
            )
        return current_user
    return _check
