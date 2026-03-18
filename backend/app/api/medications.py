"""Medications API — CRUD, dose logging, today's schedule, stock tracking."""

from datetime import date, datetime, time, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.medication import DoseLog, DoseStatus, Medication
from app.models.user import User
from app.schemas.medication import (
    DoseLogCreate, DoseLogOut, MedicationCreate,
    MedicationOut, MedicationUpdate, TodayScheduleItem,
)
from app.services.family import check_edit_access, check_view_access
from app.utils.auth import get_current_user

router = APIRouter(prefix="/medications", tags=["Medications"])

INJ_SITES = ["Left Arm", "Right Arm", "Left Thigh", "Right Thigh", "Abdomen Left", "Abdomen Right"]


@router.get("", response_model=List[MedicationOut], summary="List all medications")
async def list_medications(
    user_id: Optional[UUID] = None,
    active_only: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List medications. If user_id provided (caregiver), list that user's meds."""
    target_id = user_id or current_user.id
    if target_id != current_user.id:
        await check_view_access(current_user, target_id, db)

    query = select(Medication).where(Medication.user_id == target_id)
    if active_only:
        query = query.where(Medication.is_active == True)
    query = query.order_by(Medication.exact_hour, Medication.exact_minute)

    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=MedicationOut, status_code=201, summary="Add medication")
async def create_medication(
    med: MedicationCreate,
    for_user_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a new medication. Caregivers can add for other users."""
    target_id = for_user_id or current_user.id
    if target_id != current_user.id:
        await check_edit_access(current_user, target_id, db)

    db_med = Medication(
        user_id=target_id,
        created_by=current_user.id,
        **med.model_dump(),
    )
    db.add(db_med)
    await db.flush()
    await db.refresh(db_med)
    return db_med


@router.get("/{med_id}", response_model=MedicationOut, summary="Get medication details")
async def get_medication(
    med_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single medication by ID."""
    result = await db.execute(select(Medication).where(Medication.id == med_id))
    med = result.scalar_one_or_none()
    if not med:
        raise HTTPException(status_code=404, detail="Medication not found")
    await check_view_access(current_user, med.user_id, db)
    return med


@router.put("/{med_id}", response_model=MedicationOut, summary="Update medication")
async def update_medication(
    med_id: UUID,
    updates: MedicationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update medication details."""
    result = await db.execute(select(Medication).where(Medication.id == med_id))
    med = result.scalar_one_or_none()
    if not med:
        raise HTTPException(status_code=404, detail="Medication not found")
    await check_edit_access(current_user, med.user_id, db)

    for key, value in updates.model_dump(exclude_unset=True).items():
        setattr(med, key, value)

    await db.flush()
    await db.refresh(med)
    return med


@router.delete("/{med_id}", summary="Deactivate medication")
async def delete_medication(
    med_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete (deactivate) a medication."""
    result = await db.execute(select(Medication).where(Medication.id == med_id))
    med = result.scalar_one_or_none()
    if not med:
        raise HTTPException(status_code=404, detail="Medication not found")
    await check_edit_access(current_user, med.user_id, db)

    med.is_active = False
    return {"message": "Medication deactivated"}


@router.get("/schedule/today", response_model=List[TodayScheduleItem], summary="Today's schedule")
async def today_schedule(
    target_date: Optional[date] = None,
    user_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get today's medication schedule with dose status."""
    check_date = target_date or date.today()
    target = user_id or current_user.id
    if target != current_user.id:
        await check_view_access(current_user, target, db)

    # Get all active meds
    result = await db.execute(
        select(Medication)
        .where(and_(Medication.user_id == target, Medication.is_active == True))
        .order_by(Medication.exact_hour, Medication.exact_minute)
    )
    meds = result.scalars().all()

    # Get today's dose logs
    log_result = await db.execute(
        select(DoseLog).where(
            and_(DoseLog.user_id == target, DoseLog.scheduled_date == check_date)
        )
    )
    logs = {str(log.medication_id): log for log in log_result.scalars().all()}

    # Filter meds due on check_date and build response
    schedule = []
    now = datetime.now(timezone.utc)
    current_minutes = now.hour * 60 + now.minute

    for med in meds:
        if not _is_due_on(med, check_date):
            continue

        dose_log = logs.get(str(med.id))
        med_minutes = (med.exact_hour or 0) * 60 + (med.exact_minute or 0)
        is_today = check_date == date.today()
        is_due = is_today and current_minutes >= med_minutes and current_minutes <= med_minutes + 30 and not dose_log
        is_missed = is_today and current_minutes > med_minutes + 60 and not dose_log

        schedule.append(TodayScheduleItem(
            medication=MedicationOut.model_validate(med),
            dose_log=DoseLogOut.model_validate(dose_log) if dose_log else None,
            is_due=is_due,
            is_missed=is_missed,
        ))

    return schedule


@router.post("/{med_id}/taken", response_model=DoseLogOut, summary="Mark dose as taken")
async def mark_taken(
    med_id: UUID,
    body: DoseLogCreate = DoseLogCreate(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a medication dose as taken. Auto-decrements stock and rotates injection site."""
    result = await db.execute(select(Medication).where(Medication.id == med_id))
    med = result.scalar_one_or_none()
    if not med:
        raise HTTPException(status_code=404, detail="Medication not found")
    await check_edit_access(current_user, med.user_id, db)

    today = date.today()
    now = datetime.now(timezone.utc)

    # Check if already logged today
    existing = await db.execute(
        select(DoseLog).where(
            and_(
                DoseLog.medication_id == med_id,
                DoseLog.scheduled_date == today,
                DoseLog.status == DoseStatus.taken,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Dose already logged for today")

    # Determine injection site
    inj_site = None
    if med.form and med.form.value == "injection":
        idx = med.injection_site_index or 0
        inj_site = INJ_SITES[idx % len(INJ_SITES)]
        med.injection_site_index = (idx + 1) % len(INJ_SITES)

    # Decrement stock
    if med.stock_quantity and med.stock_quantity > 0:
        med.stock_quantity -= 1

    # Create dose log
    status_val = DoseStatus(body.status) if body.status in DoseStatus.__members__ else DoseStatus.taken
    log = DoseLog(
        medication_id=med.id,
        user_id=med.user_id,
        scheduled_date=today,
        scheduled_time=time(med.exact_hour or 0, med.exact_minute or 0) if med.exact_hour is not None else None,
        status=status_val,
        actual_time=now,
        logged_by=current_user.id,
        injection_site=inj_site,
        notes=body.notes,
    )
    db.add(log)
    await db.flush()
    await db.refresh(log)
    return log


@router.post("/{med_id}/skip", summary="Skip a dose")
async def skip_dose(
    med_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a dose as skipped."""
    result = await db.execute(select(Medication).where(Medication.id == med_id))
    med = result.scalar_one_or_none()
    if not med:
        raise HTTPException(status_code=404, detail="Medication not found")
    await check_edit_access(current_user, med.user_id, db)

    log = DoseLog(
        medication_id=med.id,
        user_id=med.user_id,
        scheduled_date=date.today(),
        status=DoseStatus.skipped,
        actual_time=datetime.now(timezone.utc),
        logged_by=current_user.id,
    )
    db.add(log)
    await db.flush()
    return {"message": "Dose skipped"}


@router.get("/{med_id}/history", response_model=List[DoseLogOut], summary="Dose history")
async def dose_history(
    med_id: UUID,
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get dose log history for a medication."""
    # Check view access via the medication's owner
    med_result = await db.execute(select(Medication).where(Medication.id == med_id))
    med = med_result.scalar_one_or_none()
    if med:
        await check_view_access(current_user, med.user_id, db)

    from datetime import timedelta
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(DoseLog)
        .where(and_(DoseLog.medication_id == med_id, DoseLog.scheduled_date >= since))
        .order_by(DoseLog.scheduled_date.desc())
    )
    return result.scalars().all()


@router.get("/stock/low", summary="Low stock medications")
async def low_stock(
    user_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get medications with low stock needing refill."""
    target = user_id or current_user.id
    if target != current_user.id:
        await check_view_access(current_user, target, db)
    result = await db.execute(
        select(Medication).where(
            and_(
                Medication.user_id == target,
                Medication.is_active == True,
                Medication.stock_quantity > 0,
                Medication.stock_quantity <= Medication.stock_alert_threshold,
            )
        )
    )
    meds = result.scalars().all()
    return [{"id": str(m.id), "name": m.name, "stock": m.stock_quantity, "threshold": m.stock_alert_threshold, "unit": m.stock_unit} for m in meds]


# ── Schedule helper ──────────────────────────────────────────
def _is_due_on(med: Medication, check_date: date) -> bool:
    """Check if a medication is due on a given date."""
    freq = med.frequency.value if med.frequency else "daily"
    if freq == "as_needed":
        return False

    start = med.start_date or date.today()
    if check_date < start:
        return False
    if med.end_date and check_date > med.end_date:
        return False

    diff_days = (check_date - start).days
    diff_months = (check_date.year - start.year) * 12 + check_date.month - start.month

    if freq == "daily" or freq == "hourly":
        return True
    elif freq == "alternate":
        return diff_days % 2 == 0
    elif freq == "custom_days":
        return check_date.weekday() in (med.freq_custom_days or [])
    elif freq == "weekly":
        # Python weekday: Mon=0, but JS: Sun=0. Stored as JS convention.
        py_day = (check_date.weekday() + 1) % 7  # Convert to Sun=0
        return py_day == (med.freq_weekly_day if med.freq_weekly_day is not None else start.weekday())
    elif freq == "biweekly":
        py_day = (check_date.weekday() + 1) % 7
        return py_day == (med.freq_weekly_day or 0) and (diff_days // 7) % 2 == 0
    elif freq == "monthly":
        return check_date.day == (med.freq_monthly_day or start.day)
    elif freq == "quarterly":
        return check_date.day == (med.freq_monthly_day or start.day) and diff_months >= 0 and diff_months % 3 == 0
    elif freq == "half_yearly":
        return check_date.day == (med.freq_monthly_day or start.day) and diff_months >= 0 and diff_months % 6 == 0
    elif freq == "yearly":
        return check_date.day == start.day and check_date.month == start.month

    return True
