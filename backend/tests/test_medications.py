"""Tests for Medications API — CRUD, dose logging, schedule."""

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, phone: str, name: str) -> str:
    """Helper: register user and return access token."""
    otp_resp = await client.post("/api/v1/auth/send-otp", json={"phone": phone})
    otp = otp_resp.json()["dev_otp"]
    token_resp = await client.post("/api/v1/auth/verify-otp", json={
        "phone": phone, "otp": otp, "name": name,
    })
    return token_resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_medication(client: AsyncClient):
    """Create a tablet medication."""
    token = await _register(client, "+913333333333", "Papa")

    resp = await client.post("/api/v1/medications", json={
        "name": "Metformin 500mg",
        "category": "medicine",
        "form": "tablet",
        "dose_amount": "1",
        "dose_unit": "tablet",
        "meal_slot": "after_breakfast",
        "exact_hour": 8,
        "exact_minute": 30,
        "frequency": "daily",
        "is_private": True,
        "stock_quantity": 30,
        "stock_alert_threshold": 5,
    }, headers=_auth(token))

    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Metformin 500mg"
    assert data["form"] == "tablet"
    assert data["dose_unit"] == "tablet"
    assert data["is_private"] is True
    assert data["stock_quantity"] == 30


@pytest.mark.asyncio
async def test_create_syrup_medication(client: AsyncClient):
    """Create a syrup with ml dosage."""
    token = await _register(client, "+914444444444", "Mummy")

    resp = await client.post("/api/v1/medications", json={
        "name": "Grilinctus Cough Syrup",
        "category": "medicine",
        "form": "syrup",
        "dose_amount": "10",
        "dose_unit": "ml",
        "meal_slot": "after_breakfast",
        "exact_hour": 8,
        "exact_minute": 30,
        "frequency": "daily",
        "stock_quantity": 1,
        "stock_unit": "bottle",
    }, headers=_auth(token))

    assert resp.status_code == 201
    data = resp.json()
    assert data["form"] == "syrup"
    assert data["dose_amount"] == "10"
    assert data["dose_unit"] == "ml"


@pytest.mark.asyncio
async def test_create_hourly_ointment(client: AsyncClient):
    """Create an ointment with hourly schedule and body area."""
    token = await _register(client, "+915555555555", "Dada")

    resp = await client.post("/api/v1/medications", json={
        "name": "Volini Gel",
        "category": "medicine",
        "form": "gel",
        "dose_amount": "1",
        "dose_unit": "application",
        "frequency": "hourly",
        "freq_hourly_interval": 4,
        "freq_hourly_from": 8,
        "freq_hourly_to": 22,
        "body_area": "Left Knee",
        "exact_hour": 8,
        "exact_minute": 0,
    }, headers=_auth(token))

    assert resp.status_code == 201
    data = resp.json()
    assert data["frequency"] == "hourly"
    assert data["freq_hourly_interval"] == 4
    assert data["body_area"] == "Left Knee"


@pytest.mark.asyncio
async def test_create_custom_days_medication(client: AsyncClient):
    """Create a medication with Mon/Wed/Fri schedule."""
    token = await _register(client, "+916666666666", "Nani")

    resp = await client.post("/api/v1/medications", json={
        "name": "Physiotherapy",
        "category": "measurement",
        "form": "tablet",
        "frequency": "custom_days",
        "freq_custom_days": [1, 3, 5],
        "exact_hour": 10,
        "exact_minute": 0,
    }, headers=_auth(token))

    assert resp.status_code == 201
    data = resp.json()
    assert data["freq_custom_days"] == [1, 3, 5]


@pytest.mark.asyncio
async def test_list_medications(client: AsyncClient):
    """List user's medications."""
    token = await _register(client, "+917777777777", "Chacha")

    # Add two meds
    await client.post("/api/v1/medications", json={
        "name": "Med A", "exact_hour": 8, "exact_minute": 0,
    }, headers=_auth(token))
    await client.post("/api/v1/medications", json={
        "name": "Med B", "exact_hour": 20, "exact_minute": 0,
    }, headers=_auth(token))

    resp = await client.get("/api/v1/medications", headers=_auth(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_update_medication(client: AsyncClient):
    """Update medication name and dosage."""
    token = await _register(client, "+918888888888", "Bua")

    create_resp = await client.post("/api/v1/medications", json={
        "name": "Old Name", "dose_amount": "1", "dose_unit": "tablet",
        "exact_hour": 8, "exact_minute": 0,
    }, headers=_auth(token))
    med_id = create_resp.json()["id"]

    update_resp = await client.put(f"/api/v1/medications/{med_id}", json={
        "name": "New Name",
        "dose_amount": "2",
        "notes": "Take with food",
    }, headers=_auth(token))

    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "New Name"
    assert update_resp.json()["dose_amount"] == "2"


@pytest.mark.asyncio
async def test_delete_medication(client: AsyncClient):
    """Soft delete deactivates medication."""
    token = await _register(client, "+919000000001", "Mama")

    create_resp = await client.post("/api/v1/medications", json={
        "name": "To Delete", "exact_hour": 8, "exact_minute": 0,
    }, headers=_auth(token))
    med_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/medications/{med_id}", headers=_auth(token))
    assert del_resp.status_code == 200

    # Should not appear in active list
    list_resp = await client.get("/api/v1/medications", headers=_auth(token))
    assert len(list_resp.json()) == 0


@pytest.mark.asyncio
async def test_mark_dose_taken(client: AsyncClient):
    """Mark a dose as taken, stock decrements."""
    token = await _register(client, "+919000000002", "Dadi")

    create_resp = await client.post("/api/v1/medications", json={
        "name": "Test Med", "stock_quantity": 10,
        "exact_hour": 8, "exact_minute": 0,
    }, headers=_auth(token))
    med_id = create_resp.json()["id"]

    taken_resp = await client.post(f"/api/v1/medications/{med_id}/taken", headers=_auth(token))
    assert taken_resp.status_code == 200
    assert taken_resp.json()["status"] == "taken"

    # Check stock decremented
    med_resp = await client.get(f"/api/v1/medications/{med_id}", headers=_auth(token))
    assert med_resp.json()["stock_quantity"] == 9


@pytest.mark.asyncio
async def test_duplicate_dose_rejected(client: AsyncClient):
    """Cannot mark dose taken twice in same day."""
    token = await _register(client, "+919000000003", "Nana")

    create_resp = await client.post("/api/v1/medications", json={
        "name": "Once Daily", "exact_hour": 8, "exact_minute": 0,
    }, headers=_auth(token))
    med_id = create_resp.json()["id"]

    await client.post(f"/api/v1/medications/{med_id}/taken", headers=_auth(token))
    dup_resp = await client.post(f"/api/v1/medications/{med_id}/taken", headers=_auth(token))
    assert dup_resp.status_code == 409


@pytest.mark.asyncio
async def test_skip_dose(client: AsyncClient):
    """Skip a dose creates a skip log."""
    token = await _register(client, "+919000000004", "Mausi")

    create_resp = await client.post("/api/v1/medications", json={
        "name": "Skip Test", "exact_hour": 8, "exact_minute": 0,
    }, headers=_auth(token))
    med_id = create_resp.json()["id"]

    skip_resp = await client.post(f"/api/v1/medications/{med_id}/skip", headers=_auth(token))
    assert skip_resp.status_code == 200


@pytest.mark.asyncio
async def test_low_stock_alert(client: AsyncClient):
    """Low stock endpoint returns meds below threshold."""
    token = await _register(client, "+919000000005", "Tau")

    await client.post("/api/v1/medications", json={
        "name": "Low Stock Med", "stock_quantity": 3, "stock_alert_threshold": 5,
        "exact_hour": 8, "exact_minute": 0,
    }, headers=_auth(token))
    await client.post("/api/v1/medications", json={
        "name": "Ok Stock Med", "stock_quantity": 50, "stock_alert_threshold": 5,
        "exact_hour": 20, "exact_minute": 0,
    }, headers=_auth(token))

    resp = await client.get("/api/v1/medications/stock/low", headers=_auth(token))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "Low Stock Med"
