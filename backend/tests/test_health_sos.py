"""Tests for Health and SOS APIs."""

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, phone: str, name: str) -> str:
    otp_resp = await client.post("/api/v1/auth/send-otp", json={"phone": phone})
    otp = otp_resp.json()["dev_otp"]
    token_resp = await client.post("/api/v1/auth/verify-otp", json={
        "phone": phone, "otp": otp, "name": name,
    })
    return token_resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_log_bp_measurement(client: AsyncClient):
    token = await _register(client, "+910000000001", "BP Test")
    resp = await client.post("/api/v1/health/measurements", json={
        "type": "bp", "value1": 120, "value2": 80, "unit": "mmHg",
    }, headers=_auth(token))
    assert resp.status_code == 201
    assert resp.json()["value1"] == 120
    assert resp.json()["value2"] == 80


@pytest.mark.asyncio
async def test_log_sugar_measurement(client: AsyncClient):
    token = await _register(client, "+910000000002", "Sugar Test")
    resp = await client.post("/api/v1/health/measurements", json={
        "type": "sugar", "value1": 145, "unit": "mg/dL",
        "notes": "Fasting",
    }, headers=_auth(token))
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_list_measurements(client: AsyncClient):
    token = await _register(client, "+910000000003", "List Test")
    await client.post("/api/v1/health/measurements", json={
        "type": "weight", "value1": 72.5, "unit": "kg",
    }, headers=_auth(token))
    await client.post("/api/v1/health/measurements", json={
        "type": "bp", "value1": 130, "value2": 85, "unit": "mmHg",
    }, headers=_auth(token))

    resp = await client.get("/api/v1/health/measurements", headers=_auth(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_log_mood(client: AsyncClient):
    token = await _register(client, "+910000000004", "Mood Test")
    resp = await client.post("/api/v1/health/moods", json={
        "mood": "good", "notes": "Feeling fine today",
    }, headers=_auth(token))
    assert resp.status_code == 201
    assert resp.json()["mood"] == "good"


@pytest.mark.asyncio
async def test_log_symptoms(client: AsyncClient):
    token = await _register(client, "+910000000005", "Sx Test")
    resp = await client.post("/api/v1/health/symptoms", json={
        "symptoms": ["Headache", "Fatigue"],
        "notes": "Since morning",
    }, headers=_auth(token))
    assert resp.status_code == 201
    assert "Headache" in resp.json()["symptoms"]


@pytest.mark.asyncio
async def test_trigger_sos(client: AsyncClient):
    token = await _register(client, "+910000000006", "SOS Test")
    resp = await client.post("/api/v1/sos/trigger", json={
        "latitude": 28.4595,
        "longitude": 77.0266,
        "notes": "Feeling dizzy",
    }, headers=_auth(token))
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "triggered"
    assert data["location_lat"] is not None


@pytest.mark.asyncio
async def test_duplicate_sos_rejected(client: AsyncClient):
    token = await _register(client, "+910000000007", "Dup SOS")
    await client.post("/api/v1/sos/trigger", json={}, headers=_auth(token))
    dup = await client.post("/api/v1/sos/trigger", json={}, headers=_auth(token))
    assert dup.status_code == 409


@pytest.mark.asyncio
async def test_acknowledge_sos(client: AsyncClient):
    token = await _register(client, "+910000000008", "Ack Test")
    trigger_resp = await client.post("/api/v1/sos/trigger", json={}, headers=_auth(token))
    alert_id = trigger_resp.json()["id"]

    ack_resp = await client.put(f"/api/v1/sos/{alert_id}/acknowledge", json={
        "notes": "On my way!",
    }, headers=_auth(token))
    assert ack_resp.status_code == 200
    assert ack_resp.json()["status"] == "acknowledged"


@pytest.mark.asyncio
async def test_resolve_sos(client: AsyncClient):
    token = await _register(client, "+910000000009", "Resolve Test")
    trigger_resp = await client.post("/api/v1/sos/trigger", json={}, headers=_auth(token))
    alert_id = trigger_resp.json()["id"]

    await client.put(f"/api/v1/sos/{alert_id}/acknowledge", json={}, headers=_auth(token))
    resolve_resp = await client.put(f"/api/v1/sos/{alert_id}/resolve", json={
        "notes": "All clear",
    }, headers=_auth(token))
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["status"] == "resolved"
