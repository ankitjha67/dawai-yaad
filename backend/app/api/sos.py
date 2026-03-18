"""SOS API — emergency alert trigger, acknowledge, resolve, history, WebSocket.

Full flow:
    Patient triggers → FCM CRITICAL to caregivers + nurses → WebSocket broadcast
    Caregiver acknowledges → FCM to patient "Help is coming" → WebSocket broadcast
    Resolved → FCM to all → WebSocket broadcast → logged with notes
"""

import json
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.hospital import PatientAssignment
from app.models.notification import Notification, NotifStatus, NotifType
from app.models.sos import SOSAlert, SOSStatus
from app.models.user import User
from app.schemas.health import SOSAcknowledge, SOSOut, SOSTrigger
from app.services.family import get_family_member_ids, get_sos_recipient_ids
from app.services.fcm import send_push, send_push_to_many
from app.utils.auth import get_current_user

router = APIRouter(prefix="/sos", tags=["SOS Emergency"])

# In-memory WebSocket connections (use Redis pub/sub in production)
_ws_connections: dict[str, list[WebSocket]] = {}


# ── WebSocket broadcast helper ───────────────────────────────

async def _broadcast_ws(user_ids: list[UUID], payload: dict):
    """Send a JSON message to all connected WebSocket clients for given user_ids."""
    msg = json.dumps(payload)
    for uid in user_ids:
        key = str(uid)
        if key in _ws_connections:
            dead = []
            for ws in _ws_connections[key]:
                try:
                    await ws.send_text(msg)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                _ws_connections[key].remove(ws)
            if not _ws_connections[key]:
                del _ws_connections[key]


async def _get_nurse_user_ids(patient_id: UUID, db: AsyncSession) -> list[UUID]:
    """Get nurse user_ids for an actively hospitalized patient."""
    result = await db.execute(
        select(PatientAssignment.nurse_id).where(
            and_(
                PatientAssignment.patient_id == patient_id,
                PatientAssignment.is_active == True,
            )
        )
    )
    return [row[0] for row in result.all()]


async def _get_fcm_tokens(user_ids: list[UUID], db: AsyncSession) -> list[str]:
    """Get FCM tokens for a list of user_ids."""
    if not user_ids:
        return []
    result = await db.execute(
        select(User.fcm_token).where(
            and_(User.id.in_(user_ids), User.fcm_token != None)
        )
    )
    return [row[0] for row in result.all() if row[0]]


# ── SOS Endpoints ────────────────────────────────────────────

@router.post("/trigger", response_model=SOSOut, status_code=201, summary="Trigger SOS alert")
async def trigger_sos(
    data: SOSTrigger,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Patient triggers SOS. Sends critical alerts to all family caregivers + assigned nurses."""
    # Check for existing active SOS
    existing = await db.execute(
        select(SOSAlert).where(
            and_(SOSAlert.user_id == current_user.id, SOSAlert.status == SOSStatus.triggered)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Active SOS already exists")

    alert = SOSAlert(
        user_id=current_user.id,
        status=SOSStatus.triggered,
        location_lat=data.latitude,
        location_lng=data.longitude,
        notes=data.notes,
    )
    db.add(alert)
    await db.flush()
    await db.refresh(alert)

    # ── FCM CRITICAL push to all family caregivers ──
    sos_recipient_ids = await get_sos_recipient_ids(current_user.id, db)
    caregiver_tokens = await _get_fcm_tokens(sos_recipient_ids, db)

    title = f"SOS from {current_user.name}!"
    body = "Emergency alert triggered. Please respond immediately."
    if data.notes:
        body = f"{data.notes}"

    fcm_data = {
        "type": "sos",
        "alert_id": str(alert.id),
        "patient_id": str(current_user.id),
        "patient_name": current_user.name,
        "status": "triggered",
    }
    if data.latitude is not None:
        fcm_data["latitude"] = str(data.latitude)
    if data.longitude is not None:
        fcm_data["longitude"] = str(data.longitude)

    if caregiver_tokens:
        send_push_to_many(
            fcm_tokens=caregiver_tokens,
            title=title,
            body=body,
            data=fcm_data,
            critical=True,
        )

    # Log notifications for caregivers
    for recipient_id in sos_recipient_ids:
        notif = Notification(
            user_id=recipient_id,
            type=NotifType.sos,
            title=title,
            body=body,
            status=NotifStatus.sent,
        )
        db.add(notif)

    # ── Alert assigned nurses if hospitalized ──
    nurse_ids = await _get_nurse_user_ids(current_user.id, db)
    if nurse_ids:
        nurse_tokens = await _get_fcm_tokens(nurse_ids, db)
        nurse_title = f"SOS: Patient {current_user.name}"
        nurse_body = "Emergency alert from patient. Immediate attention needed."

        if nurse_tokens:
            send_push_to_many(
                fcm_tokens=nurse_tokens,
                title=nurse_title,
                body=nurse_body,
                data=fcm_data,
                critical=True,
            )

        for nurse_id in nurse_ids:
            notif = Notification(
                user_id=nurse_id,
                type=NotifType.sos,
                title=nurse_title,
                body=nurse_body,
                status=NotifStatus.sent,
            )
            db.add(notif)

    # ── WebSocket broadcast to all recipients ──
    all_recipients = list(set(sos_recipient_ids + nurse_ids + [current_user.id]))
    ws_payload = {
        "type": "sos",
        "event": "triggered",
        "alert_id": str(alert.id),
        "patient_id": str(current_user.id),
        "patient_name": current_user.name,
        "status": "triggered",
    }
    if data.latitude is not None:
        ws_payload["latitude"] = data.latitude
    if data.longitude is not None:
        ws_payload["longitude"] = data.longitude

    await _broadcast_ws(all_recipients, ws_payload)

    return alert


@router.put("/{alert_id}/acknowledge", response_model=SOSOut, summary="Acknowledge SOS")
async def acknowledge_sos(
    alert_id: UUID,
    data: SOSAcknowledge = SOSAcknowledge(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Caregiver/nurse acknowledges SOS — patient gets notified help is coming."""
    result = await db.execute(select(SOSAlert).where(SOSAlert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="SOS alert not found")
    if alert.status != SOSStatus.triggered:
        raise HTTPException(status_code=400, detail="SOS already acknowledged/resolved")

    alert.status = SOSStatus.acknowledged
    alert.acknowledged_by = current_user.id
    alert.acknowledged_at = datetime.now(timezone.utc)
    if data.notes:
        alert.notes = (alert.notes or "") + f"\n[Ack by {current_user.name}]: {data.notes}"

    # ── Push to patient: "Help is coming from [Name]" ──
    patient = await db.execute(select(User).where(User.id == alert.user_id))
    patient_user = patient.scalar_one_or_none()

    if patient_user and patient_user.fcm_token:
        send_push(
            fcm_token=patient_user.fcm_token,
            title=f"Help is coming from {current_user.name}",
            body=data.notes or f"{current_user.name} has acknowledged your SOS.",
            data={
                "type": "sos",
                "alert_id": str(alert.id),
                "status": "acknowledged",
                "responder_name": current_user.name,
            },
            critical=True,
        )

    # Log notification for patient
    notif = Notification(
        user_id=alert.user_id,
        type=NotifType.sos,
        title=f"Help is coming from {current_user.name}",
        body=data.notes or f"{current_user.name} has acknowledged your SOS.",
        status=NotifStatus.sent,
    )
    db.add(notif)

    # ── WebSocket broadcast: acknowledged ──
    all_visible = await get_family_member_ids(alert.user_id, db)
    nurse_ids = await _get_nurse_user_ids(alert.user_id, db)
    all_recipients = list(set(all_visible + nurse_ids))

    await _broadcast_ws(all_recipients, {
        "type": "sos",
        "event": "acknowledged",
        "alert_id": str(alert.id),
        "patient_id": str(alert.user_id),
        "responder_id": str(current_user.id),
        "responder_name": current_user.name,
        "status": "acknowledged",
    })

    return alert


@router.put("/{alert_id}/resolve", response_model=SOSOut, summary="Resolve SOS")
async def resolve_sos(
    alert_id: UUID,
    data: SOSAcknowledge = SOSAcknowledge(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resolve an SOS alert. Notifies all parties."""
    result = await db.execute(select(SOSAlert).where(SOSAlert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="SOS alert not found")

    alert.status = SOSStatus.resolved
    alert.resolved_at = datetime.now(timezone.utc)
    if data.notes:
        alert.notes = (alert.notes or "") + f"\n[Resolved by {current_user.name}]: {data.notes}"

    # ── Push to patient ──
    patient = await db.execute(select(User).where(User.id == alert.user_id))
    patient_user = patient.scalar_one_or_none()

    title = "SOS Resolved"
    body = f"Emergency resolved by {current_user.name}."
    if data.notes:
        body += f" Note: {data.notes}"

    if patient_user and patient_user.fcm_token and alert.user_id != current_user.id:
        send_push(
            fcm_token=patient_user.fcm_token,
            title=title,
            body=body,
            data={"type": "sos", "alert_id": str(alert.id), "status": "resolved"},
        )

    # ── Push to all caregivers + nurses ──
    all_visible = await get_family_member_ids(alert.user_id, db)
    nurse_ids = await _get_nurse_user_ids(alert.user_id, db)
    all_recipients = list(set(all_visible + nurse_ids))

    # Remove the resolver from push recipients (they know they resolved it)
    notify_ids = [uid for uid in all_recipients if uid != current_user.id]
    tokens = await _get_fcm_tokens(notify_ids, db)
    if tokens:
        send_push_to_many(
            fcm_tokens=tokens,
            title=title,
            body=body,
            data={"type": "sos", "alert_id": str(alert.id), "status": "resolved"},
        )

    # Log notification
    notif = Notification(
        user_id=alert.user_id,
        type=NotifType.sos,
        title=title,
        body=body,
        status=NotifStatus.sent,
    )
    db.add(notif)

    # ── WebSocket broadcast: resolved ──
    await _broadcast_ws(all_recipients, {
        "type": "sos",
        "event": "resolved",
        "alert_id": str(alert.id),
        "patient_id": str(alert.user_id),
        "resolver_id": str(current_user.id),
        "resolver_name": current_user.name,
        "status": "resolved",
    })

    return alert


@router.get("/active", response_model=List[SOSOut], summary="Active SOS alerts")
async def active_alerts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all active (unresolved) SOS alerts visible to current user."""
    visible_ids = await get_family_member_ids(current_user.id, db)
    result = await db.execute(
        select(SOSAlert)
        .where(
            and_(
                SOSAlert.status != SOSStatus.resolved,
                SOSAlert.user_id.in_(visible_ids),
            )
        )
        .order_by(SOSAlert.triggered_at.desc())
    )
    return result.scalars().all()


@router.get("/history", response_model=List[SOSOut], summary="SOS history")
async def sos_history(
    user_id: Optional[UUID] = None,
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get SOS alert history. Defaults to current user's alerts."""
    target_id = user_id or current_user.id

    # If viewing another user's history, must be in their family
    if target_id != current_user.id:
        visible_ids = await get_family_member_ids(current_user.id, db)
        if target_id not in visible_ids:
            raise HTTPException(status_code=403, detail="Not authorized to view this user's SOS history")

    result = await db.execute(
        select(SOSAlert)
        .where(SOSAlert.user_id == target_id)
        .order_by(SOSAlert.triggered_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.websocket("/ws/{user_id}")
async def sos_websocket(websocket: WebSocket, user_id: str):
    """WebSocket for real-time SOS alerts.

    Caregivers connect to receive instant alerts for:
    - SOS triggered
    - SOS acknowledged (with responder name)
    - SOS resolved (with resolver name)

    Send "ping" to keep alive, receive "pong".
    """
    await websocket.accept()

    if user_id not in _ws_connections:
        _ws_connections[user_id] = []
    _ws_connections[user_id].append(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            # Heartbeat / keep-alive
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        if user_id in _ws_connections:
            _ws_connections[user_id].remove(websocket)
            if not _ws_connections[user_id]:
                del _ws_connections[user_id]
