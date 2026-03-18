"""Tests for SOS & Real-time — FCM push, WebSocket broadcasts, history, nurse alerts."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


async def _register(client: AsyncClient, phone: str, name: str) -> dict:
    """Helper: register user and return {access_token, user_id}."""
    otp_resp = await client.post("/api/v1/auth/send-otp", json={"phone": phone})
    otp = otp_resp.json()["dev_otp"]
    token_resp = await client.post("/api/v1/auth/verify-otp", json={
        "phone": phone, "otp": otp, "name": name,
    })
    data = token_resp.json()
    return {"access_token": data["access_token"], "user_id": data["user_id"]}


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── SOS Trigger with notifications ──────────────────────────

@pytest.mark.asyncio
async def test_sos_trigger_creates_notifications(client: AsyncClient):
    """Trigger SOS creates notifications for family caregivers."""
    patient = await _register(client, "+919300000001", "Patient")
    caregiver = await _register(client, "+919300000002", "Caregiver")

    # Create family
    family_resp = await client.post("/api/v1/families", json={"name": "SOS Family"},
                                    headers=_auth(patient["access_token"]))
    family_id = family_resp.json()["id"]

    # Add caregiver with SOS alerts
    await client.post(f"/api/v1/families/{family_id}/members", json={
        "phone": "+919300000002", "relationship": "son",
        "receives_sos": True, "can_edit": True,
    }, headers=_auth(patient["access_token"]))

    # Trigger SOS
    resp = await client.post("/api/v1/sos/trigger", json={
        "latitude": 28.4595, "longitude": 77.0266,
        "notes": "Feeling very dizzy",
    }, headers=_auth(patient["access_token"]))
    assert resp.status_code == 201
    assert resp.json()["status"] == "triggered"

    # Caregiver should have notifications
    notif_resp = await client.get("/api/v1/notifications", headers=_auth(caregiver["access_token"]))
    assert notif_resp.status_code == 200
    notifications = notif_resp.json()
    assert len(notifications) >= 1
    assert any("SOS" in n["title"] for n in notifications)


@pytest.mark.asyncio
async def test_sos_acknowledge_notifies_patient(client: AsyncClient):
    """Acknowledging SOS creates a notification for the patient."""
    patient = await _register(client, "+919300000003", "Patient2")
    caregiver = await _register(client, "+919300000004", "Caregiver2")

    # Create family
    family_resp = await client.post("/api/v1/families", json={"name": "Ack Family"},
                                    headers=_auth(patient["access_token"]))
    family_id = family_resp.json()["id"]

    await client.post(f"/api/v1/families/{family_id}/members", json={
        "phone": "+919300000004", "relationship": "son", "receives_sos": True,
    }, headers=_auth(patient["access_token"]))

    # Trigger SOS
    trigger_resp = await client.post("/api/v1/sos/trigger", json={},
                                      headers=_auth(patient["access_token"]))
    alert_id = trigger_resp.json()["id"]

    # Caregiver acknowledges
    ack_resp = await client.put(f"/api/v1/sos/{alert_id}/acknowledge", json={
        "notes": "On my way!"
    }, headers=_auth(caregiver["access_token"]))
    assert ack_resp.status_code == 200
    assert ack_resp.json()["status"] == "acknowledged"
    assert ack_resp.json()["acknowledged_by"] == caregiver["user_id"]

    # Patient should see "Help is coming" notification
    notif_resp = await client.get("/api/v1/notifications", headers=_auth(patient["access_token"]))
    notifications = notif_resp.json()
    assert any("Help is coming" in n["title"] for n in notifications)


@pytest.mark.asyncio
async def test_sos_resolve_creates_notification(client: AsyncClient):
    """Resolving SOS creates notification for patient."""
    patient = await _register(client, "+919300000005", "Patient3")

    # Trigger and resolve
    trigger_resp = await client.post("/api/v1/sos/trigger", json={},
                                      headers=_auth(patient["access_token"]))
    alert_id = trigger_resp.json()["id"]

    # Acknowledge first
    await client.put(f"/api/v1/sos/{alert_id}/acknowledge", json={},
                     headers=_auth(patient["access_token"]))

    # Resolve
    resolve_resp = await client.put(f"/api/v1/sos/{alert_id}/resolve", json={
        "notes": "All clear now"
    }, headers=_auth(patient["access_token"]))
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["status"] == "resolved"
    assert resolve_resp.json()["resolved_at"] is not None

    # Check notification
    notif_resp = await client.get("/api/v1/notifications", headers=_auth(patient["access_token"]))
    notifications = notif_resp.json()
    assert any("Resolved" in n["title"] for n in notifications)


# ── SOS History ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sos_history(client: AsyncClient):
    """SOS history returns past alerts."""
    user = await _register(client, "+919300000010", "History User")

    # Trigger and resolve one
    resp1 = await client.post("/api/v1/sos/trigger", json={},
                               headers=_auth(user["access_token"]))
    alert_id = resp1.json()["id"]
    await client.put(f"/api/v1/sos/{alert_id}/acknowledge", json={},
                     headers=_auth(user["access_token"]))
    await client.put(f"/api/v1/sos/{alert_id}/resolve", json={},
                     headers=_auth(user["access_token"]))

    # Trigger another
    await client.post("/api/v1/sos/trigger", json={},
                       headers=_auth(user["access_token"]))

    # Get history
    resp = await client.get("/api/v1/sos/history", headers=_auth(user["access_token"]))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_sos_history_family_access(client: AsyncClient):
    """Family member can view another member's SOS history."""
    patient = await _register(client, "+919300000011", "Patient History")
    caregiver = await _register(client, "+919300000012", "Caregiver History")

    # Create family
    family_resp = await client.post("/api/v1/families", json={"name": "History Fam"},
                                    headers=_auth(patient["access_token"]))
    family_id = family_resp.json()["id"]

    await client.post(f"/api/v1/families/{family_id}/members", json={
        "phone": "+919300000012", "relationship": "son",
    }, headers=_auth(patient["access_token"]))

    # Patient triggers SOS
    await client.post("/api/v1/sos/trigger", json={},
                       headers=_auth(patient["access_token"]))

    # Caregiver views patient's history
    resp = await client.get(
        f"/api/v1/sos/history?user_id={patient['user_id']}",
        headers=_auth(caregiver["access_token"]),
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_sos_history_non_family_blocked(client: AsyncClient):
    """Non-family member cannot view SOS history."""
    user_a = await _register(client, "+919300000013", "User A")
    user_b = await _register(client, "+919300000014", "User B")

    resp = await client.get(
        f"/api/v1/sos/history?user_id={user_a['user_id']}",
        headers=_auth(user_b["access_token"]),
    )
    assert resp.status_code == 403


# ── Active alerts family filtering ───────────────────────────

@pytest.mark.asyncio
async def test_active_alerts_family_only(client: AsyncClient):
    """Active alerts only shows alerts from family members."""
    user_a = await _register(client, "+919300000020", "User A Active")
    user_b = await _register(client, "+919300000021", "User B Active")

    # A triggers SOS
    await client.post("/api/v1/sos/trigger", json={},
                       headers=_auth(user_a["access_token"]))

    # B (non-family) should see nothing
    resp = await client.get("/api/v1/sos/active", headers=_auth(user_b["access_token"]))
    assert resp.status_code == 200
    assert len(resp.json()) == 0

    # A should see their own
    resp = await client.get("/api/v1/sos/active", headers=_auth(user_a["access_token"]))
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# ── Full SOS lifecycle ───────────────────────────────────────

@pytest.mark.asyncio
async def test_full_sos_lifecycle(client: AsyncClient):
    """Full SOS flow: trigger → acknowledge → resolve with location."""
    patient = await _register(client, "+919300000030", "Full Flow Patient")
    caregiver = await _register(client, "+919300000031", "Full Flow Caregiver")

    # Setup family
    family_resp = await client.post("/api/v1/families", json={"name": "Flow Family"},
                                    headers=_auth(patient["access_token"]))
    family_id = family_resp.json()["id"]

    await client.post(f"/api/v1/families/{family_id}/members", json={
        "phone": "+919300000031", "relationship": "son",
        "receives_sos": True, "can_edit": True,
    }, headers=_auth(patient["access_token"]))

    # 1. Trigger
    trigger_resp = await client.post("/api/v1/sos/trigger", json={
        "latitude": 28.6139, "longitude": 77.2090,
        "notes": "Chest pain",
    }, headers=_auth(patient["access_token"]))
    assert trigger_resp.status_code == 201
    alert = trigger_resp.json()
    alert_id = alert["id"]
    assert alert["location_lat"] is not None

    # 2. Duplicate blocked
    dup_resp = await client.post("/api/v1/sos/trigger", json={},
                                  headers=_auth(patient["access_token"]))
    assert dup_resp.status_code == 409

    # 3. Caregiver sees active alert
    active_resp = await client.get("/api/v1/sos/active",
                                    headers=_auth(caregiver["access_token"]))
    assert len(active_resp.json()) == 1

    # 4. Acknowledge
    ack_resp = await client.put(f"/api/v1/sos/{alert_id}/acknowledge", json={
        "notes": "Calling ambulance",
    }, headers=_auth(caregiver["access_token"]))
    assert ack_resp.json()["status"] == "acknowledged"

    # 5. Cannot re-acknowledge
    re_ack = await client.put(f"/api/v1/sos/{alert_id}/acknowledge", json={},
                               headers=_auth(caregiver["access_token"]))
    assert re_ack.status_code == 400

    # 6. Resolve
    resolve_resp = await client.put(f"/api/v1/sos/{alert_id}/resolve", json={
        "notes": "Patient stable",
    }, headers=_auth(caregiver["access_token"]))
    assert resolve_resp.json()["status"] == "resolved"

    # 7. No more active alerts
    active_resp = await client.get("/api/v1/sos/active",
                                    headers=_auth(caregiver["access_token"]))
    assert len(active_resp.json()) == 0

    # 8. History shows the resolved alert
    history_resp = await client.get("/api/v1/sos/history",
                                     headers=_auth(patient["access_token"]))
    assert len(history_resp.json()) == 1
    assert history_resp.json()[0]["status"] == "resolved"
