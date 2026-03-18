"""Tests for Family & Caregiver APIs — CRUD, permissions, RBAC."""

import pytest
from httpx import AsyncClient


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


# ── Family CRUD ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_family(client: AsyncClient):
    """Create a family — creator auto-added as member."""
    user = await _register(client, "+919100000001", "Papa")

    resp = await client.post("/api/v1/families", json={
        "name": "Jha Family",
    }, headers=_auth(user["access_token"]))

    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Jha Family"
    assert data["created_by"] == user["user_id"]
    assert len(data["members"]) == 1
    assert data["members"][0]["relationship"] == "self"
    assert data["members"][0]["can_edit"] is True


@pytest.mark.asyncio
async def test_list_families(client: AsyncClient):
    """User sees families they belong to."""
    user = await _register(client, "+919100000002", "Mummy")

    await client.post("/api/v1/families", json={"name": "Family A"}, headers=_auth(user["access_token"]))
    await client.post("/api/v1/families", json={"name": "Family B"}, headers=_auth(user["access_token"]))

    resp = await client.get("/api/v1/families", headers=_auth(user["access_token"]))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_get_family(client: AsyncClient):
    """Get family by ID with members."""
    user = await _register(client, "+919100000003", "Dada")

    create_resp = await client.post("/api/v1/families", json={"name": "Dada's Family"}, headers=_auth(user["access_token"]))
    family_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/families/{family_id}", headers=_auth(user["access_token"]))
    assert resp.status_code == 200
    assert resp.json()["name"] == "Dada's Family"


@pytest.mark.asyncio
async def test_update_family(client: AsyncClient):
    """Creator can update family name."""
    user = await _register(client, "+919100000004", "Nana")

    create_resp = await client.post("/api/v1/families", json={"name": "Old Name"}, headers=_auth(user["access_token"]))
    family_id = create_resp.json()["id"]

    resp = await client.put(f"/api/v1/families/{family_id}", json={"name": "New Name"}, headers=_auth(user["access_token"]))
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"


@pytest.mark.asyncio
async def test_delete_family(client: AsyncClient):
    """Creator can delete family."""
    user = await _register(client, "+919100000005", "Chacha")

    create_resp = await client.post("/api/v1/families", json={"name": "To Delete"}, headers=_auth(user["access_token"]))
    family_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/families/{family_id}", headers=_auth(user["access_token"]))
    assert resp.status_code == 200

    # Confirm deletion
    list_resp = await client.get("/api/v1/families", headers=_auth(user["access_token"]))
    assert len(list_resp.json()) == 0


# ── Member Management ────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_family_member(client: AsyncClient):
    """Add another user to the family by phone."""
    creator = await _register(client, "+919100000010", "Papa")
    member = await _register(client, "+919100000011", "Mummy")

    # Create family
    family_resp = await client.post("/api/v1/families", json={"name": "Test Family"}, headers=_auth(creator["access_token"]))
    family_id = family_resp.json()["id"]

    # Add member
    resp = await client.post(f"/api/v1/families/{family_id}/members", json={
        "phone": "+919100000011",
        "relationship": "spouse",
        "nickname": "Mummy",
        "can_edit": True,
        "receives_sos": True,
    }, headers=_auth(creator["access_token"]))

    assert resp.status_code == 201
    data = resp.json()
    assert data["user_name"] == "Mummy"
    assert data["relationship"] == "spouse"
    assert data["can_edit"] is True


@pytest.mark.asyncio
async def test_add_member_not_found(client: AsyncClient):
    """Adding nonexistent phone returns 404."""
    user = await _register(client, "+919100000012", "Papa")

    family_resp = await client.post("/api/v1/families", json={"name": "Test"}, headers=_auth(user["access_token"]))
    family_id = family_resp.json()["id"]

    resp = await client.post(f"/api/v1/families/{family_id}/members", json={
        "phone": "+919999999999",
        "relationship": "father",
    }, headers=_auth(user["access_token"]))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_add_duplicate_member(client: AsyncClient):
    """Cannot add same user twice to a family."""
    creator = await _register(client, "+919100000013", "Papa")
    member = await _register(client, "+919100000014", "Son")

    family_resp = await client.post("/api/v1/families", json={"name": "Family"}, headers=_auth(creator["access_token"]))
    family_id = family_resp.json()["id"]

    await client.post(f"/api/v1/families/{family_id}/members", json={
        "phone": "+919100000014", "relationship": "son",
    }, headers=_auth(creator["access_token"]))

    dup = await client.post(f"/api/v1/families/{family_id}/members", json={
        "phone": "+919100000014", "relationship": "son",
    }, headers=_auth(creator["access_token"]))
    assert dup.status_code == 409


@pytest.mark.asyncio
async def test_update_member_permissions(client: AsyncClient):
    """Creator can update member permissions."""
    creator = await _register(client, "+919100000015", "Papa")
    member = await _register(client, "+919100000016", "Brother")

    family_resp = await client.post("/api/v1/families", json={"name": "Family"}, headers=_auth(creator["access_token"]))
    family_id = family_resp.json()["id"]

    add_resp = await client.post(f"/api/v1/families/{family_id}/members", json={
        "phone": "+919100000016", "relationship": "brother", "can_edit": False,
    }, headers=_auth(creator["access_token"]))
    member_id = add_resp.json()["id"]

    # Grant edit permission
    resp = await client.put(f"/api/v1/families/{family_id}/members/{member_id}", json={
        "can_edit": True,
    }, headers=_auth(creator["access_token"]))
    assert resp.status_code == 200
    assert resp.json()["can_edit"] is True


@pytest.mark.asyncio
async def test_remove_member(client: AsyncClient):
    """Creator can remove a member."""
    creator = await _register(client, "+919100000017", "Papa")
    member = await _register(client, "+919100000018", "Cousin")

    family_resp = await client.post("/api/v1/families", json={"name": "Family"}, headers=_auth(creator["access_token"]))
    family_id = family_resp.json()["id"]

    add_resp = await client.post(f"/api/v1/families/{family_id}/members", json={
        "phone": "+919100000018", "relationship": "cousin",
    }, headers=_auth(creator["access_token"]))
    member_id = add_resp.json()["id"]

    resp = await client.delete(f"/api/v1/families/{family_id}/members/{member_id}", headers=_auth(creator["access_token"]))
    assert resp.status_code == 200

    # Verify family has only creator now
    family_resp = await client.get(f"/api/v1/families/{family_id}", headers=_auth(creator["access_token"]))
    assert len(family_resp.json()["members"]) == 1


@pytest.mark.asyncio
async def test_self_removal(client: AsyncClient):
    """Member can remove themselves from a family."""
    creator = await _register(client, "+919100000019", "Papa")
    member = await _register(client, "+919100000020", "Brother")

    family_resp = await client.post("/api/v1/families", json={"name": "Family"}, headers=_auth(creator["access_token"]))
    family_id = family_resp.json()["id"]

    add_resp = await client.post(f"/api/v1/families/{family_id}/members", json={
        "phone": "+919100000020", "relationship": "brother",
    }, headers=_auth(creator["access_token"]))
    member_id = add_resp.json()["id"]

    # Member removes self
    resp = await client.delete(
        f"/api/v1/families/{family_id}/members/{member_id}",
        headers=_auth(member["access_token"]),
    )
    assert resp.status_code == 200


# ── Caregiver Permission Checks ─────────────────────────────

@pytest.mark.asyncio
async def test_caregiver_can_add_medication(client: AsyncClient):
    """Caregiver with can_edit=True can add medications for family member."""
    patient = await _register(client, "+919100000030", "Dadi")
    caregiver = await _register(client, "+919100000031", "Papa")

    # Create family and add both
    family_resp = await client.post("/api/v1/families", json={"name": "Family"}, headers=_auth(caregiver["access_token"]))
    family_id = family_resp.json()["id"]

    await client.post(f"/api/v1/families/{family_id}/members", json={
        "phone": "+919100000030", "relationship": "mother", "can_edit": True,
    }, headers=_auth(caregiver["access_token"]))

    # Caregiver adds medication for patient
    resp = await client.post(
        f"/api/v1/medications?for_user_id={patient['user_id']}",
        json={"name": "BP Medicine", "exact_hour": 8, "exact_minute": 0},
        headers=_auth(caregiver["access_token"]),
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_non_family_cannot_view_meds(client: AsyncClient):
    """Non-family user cannot view another user's medications."""
    user_a = await _register(client, "+919100000032", "User A")
    user_b = await _register(client, "+919100000033", "User B")

    resp = await client.get(
        f"/api/v1/medications?user_id={user_a['user_id']}",
        headers=_auth(user_b["access_token"]),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_family_view_only_cannot_edit(client: AsyncClient):
    """Family member without can_edit cannot add medications."""
    patient = await _register(client, "+919100000034", "Dada")
    viewer = await _register(client, "+919100000035", "Grandson")

    # Create family — viewer has can_edit=False
    family_resp = await client.post("/api/v1/families", json={"name": "Family"}, headers=_auth(patient["access_token"]))
    family_id = family_resp.json()["id"]

    await client.post(f"/api/v1/families/{family_id}/members", json={
        "phone": "+919100000035", "relationship": "son", "can_edit": False,
    }, headers=_auth(patient["access_token"]))

    # Viewer can view but not edit
    resp = await client.get(
        f"/api/v1/medications?user_id={patient['user_id']}",
        headers=_auth(viewer["access_token"]),
    )
    assert resp.status_code == 200

    resp = await client.post(
        f"/api/v1/medications?for_user_id={patient['user_id']}",
        json={"name": "Test Med", "exact_hour": 8, "exact_minute": 0},
        headers=_auth(viewer["access_token"]),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_non_family_cannot_view_health(client: AsyncClient):
    """Non-family user cannot view another user's health data."""
    user_a = await _register(client, "+919100000036", "User A")
    user_b = await _register(client, "+919100000037", "User B")

    resp = await client.get(
        f"/api/v1/health/measurements?user_id={user_a['user_id']}",
        headers=_auth(user_b["access_token"]),
    )
    assert resp.status_code == 403


# ── Linked Patients ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_linked_patients(client: AsyncClient):
    """Caregiver sees their linked patients."""
    caregiver = await _register(client, "+919100000040", "Papa")
    patient_a = await _register(client, "+919100000041", "Dadi")
    patient_b = await _register(client, "+919100000042", "Dada")

    # Create family with caregiver as creator (can_edit=True)
    family_resp = await client.post("/api/v1/families", json={"name": "Family"}, headers=_auth(caregiver["access_token"]))
    family_id = family_resp.json()["id"]

    await client.post(f"/api/v1/families/{family_id}/members", json={
        "phone": "+919100000041", "relationship": "mother",
    }, headers=_auth(caregiver["access_token"]))
    await client.post(f"/api/v1/families/{family_id}/members", json={
        "phone": "+919100000042", "relationship": "father",
    }, headers=_auth(caregiver["access_token"]))

    resp = await client.get("/api/v1/families/linked-patients", headers=_auth(caregiver["access_token"]))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# ── User Profile ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_my_profile(client: AsyncClient):
    """Get own profile via /users/me."""
    user = await _register(client, "+919100000050", "My Name")
    resp = await client.get("/api/v1/users/me", headers=_auth(user["access_token"]))
    assert resp.status_code == 200
    assert resp.json()["name"] == "My Name"


@pytest.mark.asyncio
async def test_update_my_profile(client: AsyncClient):
    """Update own profile."""
    user = await _register(client, "+919100000051", "Old Name")
    resp = await client.put("/api/v1/users/me", json={
        "name": "New Name",
        "language": "hi",
    }, headers=_auth(user["access_token"]))
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"
    assert resp.json()["language"] == "hi"


@pytest.mark.asyncio
async def test_view_family_member_profile(client: AsyncClient):
    """Family member can view another member's profile."""
    user_a = await _register(client, "+919100000052", "Papa")
    user_b = await _register(client, "+919100000053", "Mummy")

    family_resp = await client.post("/api/v1/families", json={"name": "Family"}, headers=_auth(user_a["access_token"]))
    family_id = family_resp.json()["id"]

    await client.post(f"/api/v1/families/{family_id}/members", json={
        "phone": "+919100000053", "relationship": "spouse",
    }, headers=_auth(user_a["access_token"]))

    resp = await client.get(f"/api/v1/users/{user_b['user_id']}", headers=_auth(user_a["access_token"]))
    assert resp.status_code == 200
    assert resp.json()["name"] == "Mummy"


@pytest.mark.asyncio
async def test_non_family_cannot_view_profile(client: AsyncClient):
    """Non-family user cannot view another user's profile."""
    user_a = await _register(client, "+919100000054", "User A")
    user_b = await _register(client, "+919100000055", "User B")

    resp = await client.get(f"/api/v1/users/{user_a['user_id']}", headers=_auth(user_b["access_token"]))
    assert resp.status_code == 403


# ── Non-member cannot access family ─────────────────────────

@pytest.mark.asyncio
async def test_non_member_cannot_access_family(client: AsyncClient):
    """User who is not a member gets 403 on family GET."""
    creator = await _register(client, "+919100000060", "Creator")
    outsider = await _register(client, "+919100000061", "Outsider")

    family_resp = await client.post("/api/v1/families", json={"name": "Private Family"}, headers=_auth(creator["access_token"]))
    family_id = family_resp.json()["id"]

    resp = await client.get(f"/api/v1/families/{family_id}", headers=_auth(outsider["access_token"]))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_non_creator_cannot_delete_family(client: AsyncClient):
    """Non-creator member cannot delete the family."""
    creator = await _register(client, "+919100000062", "Creator")
    member = await _register(client, "+919100000063", "Member")

    family_resp = await client.post("/api/v1/families", json={"name": "Family"}, headers=_auth(creator["access_token"]))
    family_id = family_resp.json()["id"]

    await client.post(f"/api/v1/families/{family_id}/members", json={
        "phone": "+919100000063", "relationship": "brother",
    }, headers=_auth(creator["access_token"]))

    resp = await client.delete(f"/api/v1/families/{family_id}", headers=_auth(member["access_token"]))
    assert resp.status_code == 403
