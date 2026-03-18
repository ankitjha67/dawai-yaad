"""Tests for Auth API — OTP flow, JWT tokens."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root(client: AsyncClient):
    """Root endpoint returns app info."""
    resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["app"] == "Dawai Yaad"
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_send_otp(client: AsyncClient):
    """Send OTP returns dev_otp in development mode."""
    resp = await client.post("/api/v1/auth/send-otp", json={"phone": "+919876543210"})
    assert resp.status_code == 200
    data = resp.json()
    assert "dev_otp" in data
    assert len(data["dev_otp"]) == 6


@pytest.mark.asyncio
async def test_register_new_user(client: AsyncClient):
    """Full OTP registration flow for a new user."""
    # Step 1: Send OTP
    otp_resp = await client.post("/api/v1/auth/send-otp", json={"phone": "+919876543210"})
    otp = otp_resp.json()["dev_otp"]

    # Step 2: Verify OTP with name (new user)
    verify_resp = await client.post("/api/v1/auth/verify-otp", json={
        "phone": "+919876543210",
        "otp": otp,
        "name": "Ankit Jha",
    })
    assert verify_resp.status_code == 200
    data = verify_resp.json()
    assert data["name"] == "Ankit Jha"
    assert data["role"] == "patient"
    assert data["is_new_user"] is True
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_register_without_name_fails(client: AsyncClient):
    """New user must provide name."""
    otp_resp = await client.post("/api/v1/auth/send-otp", json={"phone": "+919999999999"})
    otp = otp_resp.json()["dev_otp"]

    verify_resp = await client.post("/api/v1/auth/verify-otp", json={
        "phone": "+919999999999",
        "otp": otp,
    })
    assert verify_resp.status_code == 400
    assert "Name required" in verify_resp.json()["detail"]


@pytest.mark.asyncio
async def test_invalid_otp_fails(client: AsyncClient):
    """Wrong OTP is rejected."""
    await client.post("/api/v1/auth/send-otp", json={"phone": "+919876543210"})
    verify_resp = await client.post("/api/v1/auth/verify-otp", json={
        "phone": "+919876543210",
        "otp": "000000",
        "name": "Test",
    })
    assert verify_resp.status_code == 400


@pytest.mark.asyncio
async def test_get_me_authenticated(client: AsyncClient):
    """Authenticated user can get their profile."""
    # Register
    otp_resp = await client.post("/api/v1/auth/send-otp", json={"phone": "+911111111111"})
    otp = otp_resp.json()["dev_otp"]
    token_resp = await client.post("/api/v1/auth/verify-otp", json={
        "phone": "+911111111111", "otp": otp, "name": "Papa Ji",
    })
    token = token_resp.json()["access_token"]

    # Get me
    me_resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["name"] == "Papa Ji"
    assert me_resp.json()["phone"] == "+911111111111"


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client: AsyncClient):
    """Unauthenticated request is rejected."""
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 403  # No auth header


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    """Refresh token returns new access + refresh tokens."""
    otp_resp = await client.post("/api/v1/auth/send-otp", json={"phone": "+912222222222"})
    otp = otp_resp.json()["dev_otp"]
    token_resp = await client.post("/api/v1/auth/verify-otp", json={
        "phone": "+912222222222", "otp": otp, "name": "Mummy",
    })
    refresh = token_resp.json()["refresh_token"]

    refresh_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert refresh_resp.status_code == 200
    assert "access_token" in refresh_resp.json()
