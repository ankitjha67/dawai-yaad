"""Health API — measurements, mood tracking, symptom logging."""

from datetime import date, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.health import Measurement, MoodLog, SymptomLog
from app.models.user import User
from app.schemas.health import (
    MeasurementCreate, MeasurementOut,
    MoodCreate, MoodOut,
    SymptomCreate, SymptomOut,
)
from app.utils.auth import get_current_user

router = APIRouter(prefix="/health", tags=["Health Tracking"])


# ── Measurements ─────────────────────────────────────────────
@router.post("/measurements", response_model=MeasurementOut, status_code=201)
async def create_measurement(
    data: MeasurementCreate,
    for_user_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target = for_user_id or current_user.id
    entry = Measurement(
        user_id=target,
        recorded_by=current_user.id,
        type=data.type,
        value1=data.value1,
        value2=data.value2,
        unit=data.unit,
        notes=data.notes,
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return entry


@router.get("/measurements", response_model=List[MeasurementOut])
async def list_measurements(
    user_id: Optional[UUID] = None,
    type: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target = user_id or current_user.id
    since = date.today() - timedelta(days=days)
    query = select(Measurement).where(
        and_(Measurement.user_id == target, Measurement.created_at >= since.isoformat())
    )
    if type:
        query = query.where(Measurement.type == type)
    query = query.order_by(Measurement.created_at.desc()).limit(100)
    result = await db.execute(query)
    return result.scalars().all()


# ── Mood ─────────────────────────────────────────────────────
@router.post("/moods", response_model=MoodOut, status_code=201)
async def create_mood(
    data: MoodCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entry = MoodLog(user_id=current_user.id, mood=data.mood, notes=data.notes)
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return entry


@router.get("/moods", response_model=List[MoodOut])
async def list_moods(
    user_id: Optional[UUID] = None,
    days: int = Query(30, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target = user_id or current_user.id
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(MoodLog)
        .where(and_(MoodLog.user_id == target, MoodLog.created_at >= since.isoformat()))
        .order_by(MoodLog.created_at.desc())
        .limit(100)
    )
    return result.scalars().all()


# ── Symptoms ─────────────────────────────────────────────────
@router.post("/symptoms", response_model=SymptomOut, status_code=201)
async def create_symptom(
    data: SymptomCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entry = SymptomLog(user_id=current_user.id, symptoms=data.symptoms, notes=data.notes)
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return entry


@router.get("/symptoms", response_model=List[SymptomOut])
async def list_symptoms(
    user_id: Optional[UUID] = None,
    days: int = Query(30, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target = user_id or current_user.id
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(SymptomLog)
        .where(and_(SymptomLog.user_id == target, SymptomLog.created_at >= since.isoformat()))
        .order_by(SymptomLog.created_at.desc())
        .limit(100)
    )
    return result.scalars().all()
