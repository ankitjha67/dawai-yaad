"""Tests for Reminder Engine — task logic, notifications API, escalation."""

from datetime import date, time, datetime, timezone
from unittest.mock import patch, MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.medication import DoseLog, DoseStatus, Medication
from app.models.notification import Notification, NotifType, NotifStatus
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


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Schedule helper tests ────────────────────────────────────

@pytest.mark.asyncio
async def test_is_due_daily(db_session: AsyncSession):
    """Daily medication is due every day."""
    from app.tasks.reminders import _is_due_on

    med = MagicMock()
    med.frequency = MagicMock(value="daily")
    med.start_date = date(2026, 1, 1)
    med.end_date = None
    med.freq_custom_days = None

    assert _is_due_on(med, date(2026, 3, 18)) is True
    assert _is_due_on(med, date(2026, 1, 1)) is True


@pytest.mark.asyncio
async def test_is_due_alternate(db_session: AsyncSession):
    """Alternate medication is due every other day."""
    from app.tasks.reminders import _is_due_on

    med = MagicMock()
    med.frequency = MagicMock(value="alternate")
    med.start_date = date(2026, 1, 1)
    med.end_date = None

    assert _is_due_on(med, date(2026, 1, 1)) is True   # day 0
    assert _is_due_on(med, date(2026, 1, 2)) is False  # day 1
    assert _is_due_on(med, date(2026, 1, 3)) is True   # day 2


@pytest.mark.asyncio
async def test_is_due_as_needed(db_session: AsyncSession):
    """As-needed medication is never auto-scheduled."""
    from app.tasks.reminders import _is_due_on

    med = MagicMock()
    med.frequency = MagicMock(value="as_needed")
    med.start_date = None
    med.end_date = None

    assert _is_due_on(med, date(2026, 3, 18)) is False


@pytest.mark.asyncio
async def test_is_due_respects_end_date(db_session: AsyncSession):
    """Medication past end_date is not due."""
    from app.tasks.reminders import _is_due_on

    med = MagicMock()
    med.frequency = MagicMock(value="daily")
    med.start_date = date(2026, 1, 1)
    med.end_date = date(2026, 2, 1)

    assert _is_due_on(med, date(2026, 1, 15)) is True
    assert _is_due_on(med, date(2026, 3, 1)) is False


@pytest.mark.asyncio
async def test_get_scheduled_times_single(db_session: AsyncSession):
    """Single daily medication returns one time."""
    from app.tasks.reminders import _get_scheduled_times

    med = MagicMock()
    med.frequency = MagicMock(value="daily")
    med.exact_hour = 8
    med.exact_minute = 30
    med.freq_hourly_interval = None
    med.freq_hourly_from = None

    times = _get_scheduled_times(med)
    assert len(times) == 1
    assert times[0] == time(8, 30)


@pytest.mark.asyncio
async def test_get_scheduled_times_hourly(db_session: AsyncSession):
    """Hourly medication expands to multiple times."""
    from app.tasks.reminders import _get_scheduled_times

    med = MagicMock()
    med.frequency = MagicMock(value="hourly")
    med.exact_hour = 8
    med.exact_minute = 0
    med.freq_hourly_interval = 4
    med.freq_hourly_from = 8
    med.freq_hourly_to = 20

    times = _get_scheduled_times(med)
    assert len(times) == 4  # 8, 12, 16, 20
    assert times[0] == time(8, 0)
    assert times[-1] == time(20, 0)


# ── Notifications API tests ──────────────────────────────────

@pytest.mark.asyncio
async def test_list_notifications_empty(client: AsyncClient):
    """New user has no notifications."""
    user = await _register(client, "+919200000001", "Notif Test")
    resp = await client.get("/api/v1/notifications", headers=_auth(user["access_token"]))
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_unread_count_zero(client: AsyncClient):
    """New user has 0 unread."""
    user = await _register(client, "+919200000002", "Count Test")
    resp = await client.get("/api/v1/notifications/unread-count", headers=_auth(user["access_token"]))
    assert resp.status_code == 200
    assert resp.json()["unread_count"] == 0


@pytest.mark.asyncio
async def test_create_and_read_notification(client: AsyncClient, db_session: AsyncSession):
    """Create a notification in DB, list it, mark as read."""
    user = await _register(client, "+919200000003", "Read Test")
    from uuid import UUID

    # Insert notification directly
    notif = Notification(
        user_id=UUID(user["user_id"]),
        type=NotifType.reminder,
        title="Time for Metformin",
        body="Take 1 tablet of Metformin at 8:30 AM",
        status=NotifStatus.sent,
    )
    db_session.add(notif)
    await db_session.commit()
    await db_session.refresh(notif)
    notif_id = str(notif.id)

    # List notifications
    resp = await client.get("/api/v1/notifications", headers=_auth(user["access_token"]))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Time for Metformin"
    assert data[0]["read_at"] is None

    # Check unread count
    resp = await client.get("/api/v1/notifications/unread-count", headers=_auth(user["access_token"]))
    assert resp.json()["unread_count"] == 1

    # Mark as read
    resp = await client.put(f"/api/v1/notifications/{notif_id}/read", headers=_auth(user["access_token"]))
    assert resp.status_code == 200
    assert resp.json()["read_at"] is not None
    assert resp.json()["status"] == "read"

    # Unread count should be 0
    resp = await client.get("/api/v1/notifications/unread-count", headers=_auth(user["access_token"]))
    assert resp.json()["unread_count"] == 0


@pytest.mark.asyncio
async def test_mark_all_read(client: AsyncClient, db_session: AsyncSession):
    """Mark all notifications as read."""
    user = await _register(client, "+919200000004", "All Read")
    from uuid import UUID

    for i in range(3):
        notif = Notification(
            user_id=UUID(user["user_id"]),
            type=NotifType.reminder,
            title=f"Reminder {i}",
            body=f"Body {i}",
            status=NotifStatus.sent,
        )
        db_session.add(notif)
    await db_session.commit()

    # Confirm 3 unread
    resp = await client.get("/api/v1/notifications/unread-count", headers=_auth(user["access_token"]))
    assert resp.json()["unread_count"] == 3

    # Mark all read
    resp = await client.put("/api/v1/notifications/read-all", headers=_auth(user["access_token"]))
    assert resp.status_code == 200

    # Confirm 0 unread
    resp = await client.get("/api/v1/notifications/unread-count", headers=_auth(user["access_token"]))
    assert resp.json()["unread_count"] == 0


@pytest.mark.asyncio
async def test_filter_notifications_by_type(client: AsyncClient, db_session: AsyncSession):
    """Filter notifications by type."""
    user = await _register(client, "+919200000005", "Filter Test")
    from uuid import UUID

    notif1 = Notification(
        user_id=UUID(user["user_id"]),
        type=NotifType.reminder,
        title="Reminder",
        status=NotifStatus.sent,
    )
    notif2 = Notification(
        user_id=UUID(user["user_id"]),
        type=NotifType.missed_dose,
        title="Missed",
        status=NotifStatus.sent,
    )
    db_session.add_all([notif1, notif2])
    await db_session.commit()

    # All
    resp = await client.get("/api/v1/notifications", headers=_auth(user["access_token"]))
    assert len(resp.json()) == 2

    # Filter by reminder
    resp = await client.get("/api/v1/notifications?type=reminder", headers=_auth(user["access_token"]))
    assert len(resp.json()) == 1
    assert resp.json()[0]["type"] == "reminder"


@pytest.mark.asyncio
async def test_unread_only_filter(client: AsyncClient, db_session: AsyncSession):
    """Filter for unread-only notifications."""
    user = await _register(client, "+919200000006", "Unread Test")
    from uuid import UUID

    notif1 = Notification(
        user_id=UUID(user["user_id"]),
        type=NotifType.reminder,
        title="Unread",
        status=NotifStatus.sent,
    )
    notif2 = Notification(
        user_id=UUID(user["user_id"]),
        type=NotifType.reminder,
        title="Read",
        status=NotifStatus.read,
        read_at=datetime.now(timezone.utc),
    )
    db_session.add_all([notif1, notif2])
    await db_session.commit()

    # All
    resp = await client.get("/api/v1/notifications", headers=_auth(user["access_token"]))
    assert len(resp.json()) == 2

    # Unread only
    resp = await client.get("/api/v1/notifications?unread_only=true", headers=_auth(user["access_token"]))
    assert len(resp.json()) == 1
    assert resp.json()[0]["title"] == "Unread"


# ── FCM service tests ────────────────────────────────────────

@pytest.mark.asyncio
async def test_fcm_dev_mode(db_session: AsyncSession):
    """FCM in dev mode logs but returns True."""
    from app.services.fcm import send_push

    result = send_push(
        fcm_token="fake_token_abc123",
        title="Test Push",
        body="This is a test",
    )
    assert result is True


@pytest.mark.asyncio
async def test_fcm_no_token(db_session: AsyncSession):
    """FCM with no token returns False."""
    from app.services.fcm import send_push

    result = send_push(fcm_token="", title="Test", body="Test")
    assert result is False


@pytest.mark.asyncio
async def test_send_push_to_many(db_session: AsyncSession):
    """send_push_to_many counts successful sends."""
    from app.services.fcm import send_push_to_many

    count = send_push_to_many(
        fcm_tokens=["token_a", "token_b", "token_c"],
        title="Test",
        body="Multi",
    )
    assert count == 3
