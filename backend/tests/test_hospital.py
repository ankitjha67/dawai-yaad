"""Tests for Hospital/Nurse API — CRUD, staff, assignments, dashboard, dose admin."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole


async def _register(client: AsyncClient, phone: str, name: str) -> dict:
    """Helper: register user and return {access_token, user_id}."""
    otp_resp = await client.post("/api/v1/auth/send-otp", json={"phone": phone})
    otp = otp_resp.json()["dev_otp"]
    token_resp = await client.post("/api/v1/auth/verify-otp", json={
        "phone": phone, "otp": otp, "name": name,
    })
    data = token_resp.json()
    return {"access_token": data["access_token"], "user_id": data["user_id"]}


async def _register_admin(client: AsyncClient, db_session: AsyncSession, phone: str, name: str) -> dict:
    """Register user and set role to admin."""
    user = await _register(client, phone, name)
    from uuid import UUID
    result = await db_session.execute(
        User.__table__.update().where(User.__table__.c.id == UUID(user["user_id"])).values(role="admin")
    )
    await db_session.commit()

    # Re-login to get token with admin role
    otp_resp = await client.post("/api/v1/auth/send-otp", json={"phone": phone})
    otp = otp_resp.json()["dev_otp"]
    token_resp = await client.post("/api/v1/auth/verify-otp", json={
        "phone": phone, "otp": otp,
    })
    data = token_resp.json()
    return {"access_token": data["access_token"], "user_id": data["user_id"]}


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Hospital CRUD ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_hospital(client: AsyncClient, db_session: AsyncSession):
    """Admin can create a hospital."""
    admin = await _register_admin(client, db_session, "+919400000001", "Admin")

    resp = await client.post("/api/v1/hospitals", json={
        "name": "City General Hospital",
        "address": "123 Main Street",
        "city": "Mumbai",
        "phone": "+912233445566",
    }, headers=_auth(admin["access_token"]))

    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "City General Hospital"
    assert data["city"] == "Mumbai"


@pytest.mark.asyncio
async def test_patient_cannot_create_hospital(client: AsyncClient):
    """Patient role cannot create a hospital."""
    patient = await _register(client, "+919400000002", "Patient")

    resp = await client.post("/api/v1/hospitals", json={
        "name": "Test Hospital",
    }, headers=_auth(patient["access_token"]))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_hospitals(client: AsyncClient, db_session: AsyncSession):
    """List hospitals."""
    admin = await _register_admin(client, db_session, "+919400000003", "Admin2")

    await client.post("/api/v1/hospitals", json={"name": "Hospital A", "city": "Delhi"},
                       headers=_auth(admin["access_token"]))
    await client.post("/api/v1/hospitals", json={"name": "Hospital B", "city": "Mumbai"},
                       headers=_auth(admin["access_token"]))

    # List all
    resp = await client.get("/api/v1/hospitals", headers=_auth(admin["access_token"]))
    assert resp.status_code == 200
    assert len(resp.json()) >= 2

    # Filter by city
    resp = await client.get("/api/v1/hospitals?city=Delhi", headers=_auth(admin["access_token"]))
    assert all(h["city"] == "Delhi" for h in resp.json())


# ── Staff Management ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_and_list_staff(client: AsyncClient, db_session: AsyncSession):
    """Add nurse to hospital staff and list."""
    admin = await _register_admin(client, db_session, "+919400000010", "Admin Staff")
    nurse = await _register(client, "+919400000011", "Nurse Priya")

    # Create hospital
    hosp_resp = await client.post("/api/v1/hospitals", json={"name": "Staff Hospital"},
                                   headers=_auth(admin["access_token"]))
    hospital_id = hosp_resp.json()["id"]

    # Add nurse as staff
    staff_resp = await client.post(f"/api/v1/hospitals/{hospital_id}/staff", json={
        "phone": "+919400000011",
        "department": "General Ward",
        "shift": "morning",
    }, headers=_auth(admin["access_token"]))
    assert staff_resp.status_code == 201
    assert staff_resp.json()["user_name"] == "Nurse Priya"
    assert staff_resp.json()["department"] == "General Ward"

    # List staff
    list_resp = await client.get(f"/api/v1/hospitals/{hospital_id}/staff",
                                  headers=_auth(admin["access_token"]))
    assert len(list_resp.json()) == 1


@pytest.mark.asyncio
async def test_duplicate_staff_rejected(client: AsyncClient, db_session: AsyncSession):
    """Cannot add same user twice as staff."""
    admin = await _register_admin(client, db_session, "+919400000012", "Admin Dup")
    nurse = await _register(client, "+919400000013", "Nurse Dup")

    hosp_resp = await client.post("/api/v1/hospitals", json={"name": "Dup Hospital"},
                                   headers=_auth(admin["access_token"]))
    hospital_id = hosp_resp.json()["id"]

    await client.post(f"/api/v1/hospitals/{hospital_id}/staff", json={
        "phone": "+919400000013",
    }, headers=_auth(admin["access_token"]))

    dup = await client.post(f"/api/v1/hospitals/{hospital_id}/staff", json={
        "phone": "+919400000013",
    }, headers=_auth(admin["access_token"]))
    assert dup.status_code == 409


# ── Patient Assignment ───────────────────────────────────────

@pytest.mark.asyncio
async def test_assign_patient(client: AsyncClient, db_session: AsyncSession):
    """Assign patient to nurse with ward/bed."""
    admin = await _register_admin(client, db_session, "+919400000020", "Admin Assign")
    nurse = await _register(client, "+919400000021", "Nurse Assign")
    patient = await _register(client, "+919400000022", "Patient Assign")

    # Setup hospital + staff
    hosp_resp = await client.post("/api/v1/hospitals", json={"name": "Assign Hospital"},
                                   headers=_auth(admin["access_token"]))
    hospital_id = hosp_resp.json()["id"]

    staff_resp = await client.post(f"/api/v1/hospitals/{hospital_id}/staff", json={
        "phone": "+919400000021",
    }, headers=_auth(admin["access_token"]))

    # Assign patient
    assign_resp = await client.post(f"/api/v1/hospitals/{hospital_id}/assignments", json={
        "patient_phone": "+919400000022",
        "nurse_id": nurse["user_id"],
        "ward": "ICU",
        "bed_number": "B-12",
    }, headers=_auth(admin["access_token"]))
    assert assign_resp.status_code == 201
    data = assign_resp.json()
    assert data["patient_name"] == "Patient Assign"
    assert data["nurse_name"] == "Nurse Assign"
    assert data["ward"] == "ICU"
    assert data["bed_number"] == "B-12"


@pytest.mark.asyncio
async def test_discharge_patient(client: AsyncClient, db_session: AsyncSession):
    """Discharge auto-deactivates assignment."""
    admin = await _register_admin(client, db_session, "+919400000023", "Admin Discharge")
    nurse = await _register(client, "+919400000024", "Nurse Discharge")
    patient = await _register(client, "+919400000025", "Patient Discharge")

    hosp_resp = await client.post("/api/v1/hospitals", json={"name": "Discharge Hospital"},
                                   headers=_auth(admin["access_token"]))
    hospital_id = hosp_resp.json()["id"]

    await client.post(f"/api/v1/hospitals/{hospital_id}/staff", json={
        "phone": "+919400000024",
    }, headers=_auth(admin["access_token"]))

    assign_resp = await client.post(f"/api/v1/hospitals/{hospital_id}/assignments", json={
        "patient_phone": "+919400000025",
        "nurse_id": nurse["user_id"],
        "ward": "General",
        "bed_number": "G-5",
    }, headers=_auth(admin["access_token"]))
    assignment_id = assign_resp.json()["id"]

    # Discharge
    update_resp = await client.put(
        f"/api/v1/hospitals/{hospital_id}/assignments/{assignment_id}",
        json={"discharged_date": "2026-03-18"},
        headers=_auth(admin["access_token"]),
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["is_active"] is False
    assert update_resp.json()["discharged_date"] == "2026-03-18"


# ── Nurse Dose Administration ────────────────────────────────

@pytest.mark.asyncio
async def test_nurse_administer_dose(client: AsyncClient, db_session: AsyncSession):
    """Nurse can administer dose for assigned patient."""
    admin = await _register_admin(client, db_session, "+919400000030", "Admin Dose")
    nurse = await _register(client, "+919400000031", "Nurse Dose")
    patient = await _register(client, "+919400000032", "Patient Dose")

    # Setup
    hosp_resp = await client.post("/api/v1/hospitals", json={"name": "Dose Hospital"},
                                   headers=_auth(admin["access_token"]))
    hospital_id = hosp_resp.json()["id"]

    await client.post(f"/api/v1/hospitals/{hospital_id}/staff", json={
        "phone": "+919400000031",
    }, headers=_auth(admin["access_token"]))

    await client.post(f"/api/v1/hospitals/{hospital_id}/assignments", json={
        "patient_phone": "+919400000032",
        "nurse_id": nurse["user_id"],
        "ward": "ICU",
        "bed_number": "I-3",
    }, headers=_auth(admin["access_token"]))

    # Patient creates medication
    med_resp = await client.post("/api/v1/medications", json={
        "name": "Paracetamol IV",
        "form": "injection",
        "exact_hour": 8,
        "exact_minute": 0,
        "stock_quantity": 10,
    }, headers=_auth(patient["access_token"]))
    med_id = med_resp.json()["id"]

    # Nurse administers
    admin_resp = await client.post(
        f"/api/v1/hospitals/{hospital_id}/administer/{med_id}",
        headers=_auth(nurse["access_token"]),
    )
    assert admin_resp.status_code == 200
    data = admin_resp.json()
    assert data["administered_by"] == "Nurse Dose"
    assert data["injection_site"] is not None

    # Verify stock decremented
    med_detail = await client.get(f"/api/v1/medications/{med_id}",
                                   headers=_auth(patient["access_token"]))
    assert med_detail.json()["stock_quantity"] == 9


@pytest.mark.asyncio
async def test_unassigned_nurse_cannot_administer(client: AsyncClient, db_session: AsyncSession):
    """Nurse not assigned to patient gets 403."""
    admin = await _register_admin(client, db_session, "+919400000033", "Admin Unassign")
    nurse = await _register(client, "+919400000034", "Nurse Unassign")
    patient = await _register(client, "+919400000035", "Patient Unassign")

    hosp_resp = await client.post("/api/v1/hospitals", json={"name": "Unassign Hospital"},
                                   headers=_auth(admin["access_token"]))
    hospital_id = hosp_resp.json()["id"]

    # Add nurse as staff but don't assign patient
    await client.post(f"/api/v1/hospitals/{hospital_id}/staff", json={
        "phone": "+919400000034",
    }, headers=_auth(admin["access_token"]))

    med_resp = await client.post("/api/v1/medications", json={
        "name": "Test Med", "exact_hour": 8, "exact_minute": 0,
    }, headers=_auth(patient["access_token"]))
    med_id = med_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/hospitals/{hospital_id}/administer/{med_id}",
        headers=_auth(nurse["access_token"]),
    )
    assert resp.status_code == 403


# ── Non-staff cannot access ──────────────────────────────────

@pytest.mark.asyncio
async def test_non_staff_cannot_list_assignments(client: AsyncClient, db_session: AsyncSession):
    """Non-staff user cannot list assignments."""
    admin = await _register_admin(client, db_session, "+919400000040", "Admin Access")
    outsider = await _register(client, "+919400000041", "Outsider")

    hosp_resp = await client.post("/api/v1/hospitals", json={"name": "Access Hospital"},
                                   headers=_auth(admin["access_token"]))
    hospital_id = hosp_resp.json()["id"]

    resp = await client.get(f"/api/v1/hospitals/{hospital_id}/assignments",
                             headers=_auth(outsider["access_token"]))
    assert resp.status_code == 403
