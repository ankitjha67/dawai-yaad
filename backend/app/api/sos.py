"""SOS API — emergency alert trigger, acknowledge, resolve."""

from datetime import datetime, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.sos import SOSAlert, SOSStatus
from app.models.user import User
from app.schemas.health import SOSAcknowledge, SOSOut, SOSTrigger
from app.services.family import get_family_member_ids, get_sos_recipient_ids
from app.utils.auth import get_current_user

router = APIRouter(prefix="/sos", tags=["SOS Emergency"])

# In-memory WebSocket connections (use Redis pub/sub in production)
_ws_connections: dict[str, list[WebSocket]] = {}


@router.post("/trigger", response_model=SOSOut, status_code=201, summary="Trigger SOS alert")
async def trigger_sos(
    data: SOSTrigger,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Patient triggers SOS. Sends critical alerts to all family caregivers."""
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

    # TODO: Send FCM critical push to all caregivers
    # TODO: Send SMS to emergency contacts
    # TODO: Broadcast via WebSocket

    # Notify all family members who receive SOS via WebSocket
    sos_recipients = await get_sos_recipient_ids(current_user.id, db)
    msg = f'{{"type":"sos","user":"{current_user.name}","alert_id":"{alert.id}","status":"triggered"}}'
    for recipient_id in sos_recipients:
        key = str(recipient_id)
        if key in _ws_connections:
            for ws in _ws_connections[key]:
                try:
                    await ws.send_text(msg)
                except Exception:
                    pass
    # Also notify via self key (backwards compat)
    self_key = str(current_user.id)
    if self_key in _ws_connections:
        for ws in _ws_connections[self_key]:
            try:
                await ws.send_text(msg)
            except Exception:
                pass

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

    # TODO: Push to patient "Help is coming from [name]"

    return alert


@router.put("/{alert_id}/resolve", response_model=SOSOut, summary="Resolve SOS")
async def resolve_sos(
    alert_id: UUID,
    data: SOSAcknowledge = SOSAcknowledge(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resolve an SOS alert."""
    result = await db.execute(select(SOSAlert).where(SOSAlert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="SOS alert not found")

    alert.status = SOSStatus.resolved
    alert.resolved_at = datetime.now(timezone.utc)
    if data.notes:
        alert.notes = (alert.notes or "") + f"\n[Resolved by {current_user.name}]: {data.notes}"

    return alert


@router.get("/active", response_model=List[SOSOut], summary="Active SOS alerts")
async def active_alerts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all active (unresolved) SOS alerts visible to current user."""
    # Filter to alerts from family members (or self)
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


@router.websocket("/ws/{user_id}")
async def sos_websocket(websocket: WebSocket, user_id: str):
    """WebSocket for real-time SOS alerts. Caregivers connect to receive instant alerts."""
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
        _ws_connections[user_id].remove(websocket)
        if not _ws_connections[user_id]:
            del _ws_connections[user_id]
