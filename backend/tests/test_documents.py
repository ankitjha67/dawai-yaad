"""Tests for Documents & Reports API — upload, list, download, PDF generation."""

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


# ── Document Upload ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_upload_document(client: AsyncClient):
    """Upload a document for self."""
    user = await _register(client, "+919500000001", "Upload User")

    resp = await client.post(
        "/api/v1/documents",
        data={"title": "Blood Report March", "type": "blood_report", "notes": "Fasting blood test"},
        files={"file": ("report.pdf", b"fake pdf content", "application/pdf")},
        headers=_auth(user["access_token"]),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Blood Report March"
    assert data["type"] == "blood_report"
    assert data["file_url"] is not None
    assert data["uploaded_by_name"] == "Upload User"


@pytest.mark.asyncio
async def test_upload_for_family_member(client: AsyncClient):
    """Caregiver uploads document for family member."""
    caregiver = await _register(client, "+919500000002", "Caregiver Doc")
    patient = await _register(client, "+919500000003", "Patient Doc")

    # Create family
    family_resp = await client.post("/api/v1/families", json={"name": "Doc Family"},
                                    headers=_auth(caregiver["access_token"]))
    family_id = family_resp.json()["id"]

    await client.post(f"/api/v1/families/{family_id}/members", json={
        "phone": "+919500000003", "relationship": "mother", "can_edit": True,
    }, headers=_auth(caregiver["access_token"]))

    # Upload for patient
    resp = await client.post(
        f"/api/v1/documents?for_user_id={patient['user_id']}",
        data={"title": "X-Ray Report", "type": "xray"},
        files={"file": ("xray.jpg", b"fake image data", "image/jpeg")},
        headers=_auth(caregiver["access_token"]),
    )
    assert resp.status_code == 201
    assert resp.json()["user_id"] == patient["user_id"]


@pytest.mark.asyncio
async def test_non_family_cannot_upload(client: AsyncClient):
    """Non-family user cannot upload for another user."""
    user_a = await _register(client, "+919500000004", "User A")
    user_b = await _register(client, "+919500000005", "User B")

    resp = await client.post(
        f"/api/v1/documents?for_user_id={user_a['user_id']}",
        data={"title": "Unauthorized"},
        files={"file": ("test.txt", b"data", "text/plain")},
        headers=_auth(user_b["access_token"]),
    )
    assert resp.status_code == 403


# ── List Documents ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_documents(client: AsyncClient):
    """List own documents."""
    user = await _register(client, "+919500000010", "List User")

    # Upload two docs
    for i in range(2):
        await client.post(
            "/api/v1/documents",
            data={"title": f"Doc {i}", "type": "prescription"},
            files={"file": (f"doc{i}.pdf", b"content", "application/pdf")},
            headers=_auth(user["access_token"]),
        )

    resp = await client.get("/api/v1/documents", headers=_auth(user["access_token"]))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_filter_documents_by_type(client: AsyncClient):
    """Filter documents by type."""
    user = await _register(client, "+919500000011", "Filter User")

    await client.post(
        "/api/v1/documents",
        data={"title": "Report", "type": "blood_report"},
        files={"file": ("r.pdf", b"content", "application/pdf")},
        headers=_auth(user["access_token"]),
    )
    await client.post(
        "/api/v1/documents",
        data={"title": "Prescription", "type": "prescription"},
        files={"file": ("p.pdf", b"content", "application/pdf")},
        headers=_auth(user["access_token"]),
    )

    resp = await client.get("/api/v1/documents?type=blood_report",
                             headers=_auth(user["access_token"]))
    assert len(resp.json()) == 1
    assert resp.json()[0]["type"] == "blood_report"


# ── Get / Delete ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_document(client: AsyncClient):
    """Get single document by ID."""
    user = await _register(client, "+919500000012", "Get User")

    upload_resp = await client.post(
        "/api/v1/documents",
        data={"title": "My Doc"},
        files={"file": ("doc.pdf", b"content", "application/pdf")},
        headers=_auth(user["access_token"]),
    )
    doc_id = upload_resp.json()["id"]

    resp = await client.get(f"/api/v1/documents/{doc_id}", headers=_auth(user["access_token"]))
    assert resp.status_code == 200
    assert resp.json()["title"] == "My Doc"


@pytest.mark.asyncio
async def test_delete_document(client: AsyncClient):
    """Delete a document."""
    user = await _register(client, "+919500000013", "Delete User")

    upload_resp = await client.post(
        "/api/v1/documents",
        data={"title": "To Delete"},
        files={"file": ("del.pdf", b"content", "application/pdf")},
        headers=_auth(user["access_token"]),
    )
    doc_id = upload_resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/documents/{doc_id}",
                                    headers=_auth(user["access_token"]))
    assert del_resp.status_code == 200

    # Verify deleted
    list_resp = await client.get("/api/v1/documents", headers=_auth(user["access_token"]))
    assert len(list_resp.json()) == 0


# ── PDF Report ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_adherence_report(client: AsyncClient):
    """Generate adherence report returns content."""
    user = await _register(client, "+919500000020", "Report User")

    # Add a medication and take a dose
    med_resp = await client.post("/api/v1/medications", json={
        "name": "Test Med", "exact_hour": 8, "exact_minute": 0,
    }, headers=_auth(user["access_token"]))
    med_id = med_resp.json()["id"]

    await client.post(f"/api/v1/medications/{med_id}/taken",
                       headers=_auth(user["access_token"]))

    # Generate report
    resp = await client.get("/api/v1/documents/report/adherence",
                             headers=_auth(user["access_token"]))
    assert resp.status_code == 200
    assert len(resp.content) > 0
    # Should contain HTML or PDF content
    assert b"Dawai Yaad" in resp.content or b"%PDF" in resp.content


@pytest.mark.asyncio
async def test_adherence_report_for_family(client: AsyncClient):
    """Caregiver can generate report for family member."""
    caregiver = await _register(client, "+919500000021", "Caregiver Report")
    patient = await _register(client, "+919500000022", "Patient Report")

    # Create family
    family_resp = await client.post("/api/v1/families", json={"name": "Report Family"},
                                    headers=_auth(caregiver["access_token"]))
    family_id = family_resp.json()["id"]

    await client.post(f"/api/v1/families/{family_id}/members", json={
        "phone": "+919500000022", "relationship": "mother",
    }, headers=_auth(caregiver["access_token"]))

    resp = await client.get(
        f"/api/v1/documents/report/adherence?user_id={patient['user_id']}",
        headers=_auth(caregiver["access_token"]),
    )
    assert resp.status_code == 200


# ── Storage service ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_storage_dev_mode(db_session: AsyncSession):
    """Storage service works in dev mode (no MinIO)."""
    from app.services.storage import upload_file, get_presigned_url, delete_file

    object_name, size = upload_file(b"test data", "test.txt")
    assert size == 9
    assert "documents/" in object_name

    url = get_presigned_url(object_name)
    assert object_name in url

    assert delete_file(object_name) is True
