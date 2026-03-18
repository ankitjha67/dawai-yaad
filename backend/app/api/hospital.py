"""Hospital/Nurse API — hospital CRUD, staff, patient assignment, nurse dashboard."""

from datetime import date, datetime, time, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.hospital import Hospital, HospitalStaff, PatientAssignment
from app.models.medication import DoseLog, DoseStatus, Medication
from app.models.user import User, UserRole
from app.schemas.hospital import (
    AssignmentCreate,
    AssignmentOut,
    AssignmentUpdate,
    HospitalCreate,
    HospitalOut,
    HospitalUpdate,
    NursePatientSchedule,
    StaffAdd,
    StaffOut,
    StaffUpdate,
)
from app.schemas.medication import DoseLogOut, MedicationOut, TodayScheduleItem
from app.utils.auth import get_current_user, require_roles

router = APIRouter(prefix="/hospitals", tags=["Hospital & Nurse"])


# ── Helpers ──────────────────────────────────────────────────

async def _require_hospital_staff(
    hospital_id: UUID, user: User, db: AsyncSession
) -> HospitalStaff:
    """Raise 403 if user is not active staff at this hospital (admins bypass)."""
    if user.role == UserRole.admin:
        # Return a dummy for admins
        return HospitalStaff(hospital_id=hospital_id, user_id=user.id, is_active=True)

    result = await db.execute(
        select(HospitalStaff).where(
            and_(
                HospitalStaff.hospital_id == hospital_id,
                HospitalStaff.user_id == user.id,
                HospitalStaff.is_active == True,
            )
        )
    )
    staff = result.scalar_one_or_none()
    if not staff:
        raise HTTPException(status_code=403, detail="Not authorized — not staff at this hospital")
    return staff


def _is_due_on(med: Medication, check_date: date) -> bool:
    """Check if a medication is due on a given date (mirrors api/medications.py)."""
    freq = med.frequency.value if med.frequency else "daily"
    if freq == "as_needed":
        return False
    start = med.start_date or check_date
    if check_date < start:
        return False
    if med.end_date and check_date > med.end_date:
        return False
    diff_days = (check_date - start).days
    diff_months = (check_date.year - start.year) * 12 + check_date.month - start.month
    if freq in ("daily", "hourly"):
        return True
    elif freq == "alternate":
        return diff_days % 2 == 0
    elif freq == "custom_days":
        return check_date.weekday() in (med.freq_custom_days or [])
    elif freq == "weekly":
        py_day = (check_date.weekday() + 1) % 7
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


# ── Hospital CRUD ────────────────────────────────────────────

@router.post("", response_model=HospitalOut, status_code=201, summary="Register hospital")
async def create_hospital(
    data: HospitalCreate,
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.doctor)),
    db: AsyncSession = Depends(get_db),
):
    """Register a new hospital. Admin or doctor only."""
    hospital = Hospital(name=data.name, address=data.address, city=data.city, phone=data.phone)
    db.add(hospital)
    await db.flush()
    await db.refresh(hospital)
    return hospital


@router.get("", response_model=List[HospitalOut], summary="List hospitals")
async def list_hospitals(
    city: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all active hospitals."""
    query = select(Hospital).where(Hospital.is_active == True)
    if city:
        query = query.where(Hospital.city == city)
    query = query.order_by(Hospital.name)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{hospital_id}", response_model=HospitalOut, summary="Get hospital details")
async def get_hospital(
    hospital_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get hospital details."""
    result = await db.execute(select(Hospital).where(Hospital.id == hospital_id))
    hospital = result.scalar_one_or_none()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
    return hospital


@router.put("/{hospital_id}", response_model=HospitalOut, summary="Update hospital")
async def update_hospital(
    hospital_id: UUID,
    data: HospitalUpdate,
    current_user: User = Depends(require_roles(UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    """Update hospital info. Admin only."""
    result = await db.execute(select(Hospital).where(Hospital.id == hospital_id))
    hospital = result.scalar_one_or_none()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(hospital, key, value)

    await db.flush()
    await db.refresh(hospital)
    return hospital


# ── Staff Management ─────────────────────────────────────────

@router.post(
    "/{hospital_id}/staff",
    response_model=StaffOut,
    status_code=201,
    summary="Add staff member",
)
async def add_staff(
    hospital_id: UUID,
    data: StaffAdd,
    current_user: User = Depends(require_roles(UserRole.admin, UserRole.doctor)),
    db: AsyncSession = Depends(get_db),
):
    """Add a nurse/doctor to hospital staff by phone number."""
    # Verify hospital exists
    hosp_result = await db.execute(select(Hospital).where(Hospital.id == hospital_id))
    if not hosp_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Hospital not found")

    # Look up user
    user_result = await db.execute(select(User).where(User.phone == data.phone))
    target_user = user_result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found with this phone number")

    # Check duplicate
    existing = await db.execute(
        select(HospitalStaff).where(
            and_(
                HospitalStaff.hospital_id == hospital_id,
                HospitalStaff.user_id == target_user.id,
                HospitalStaff.is_active == True,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="User is already staff at this hospital")

    staff = HospitalStaff(
        hospital_id=hospital_id,
        user_id=target_user.id,
        department=data.department,
        employee_id=data.employee_id,
        shift=data.shift,
    )
    db.add(staff)
    await db.flush()
    await db.refresh(staff)

    return StaffOut(
        id=staff.id,
        hospital_id=staff.hospital_id,
        user_id=staff.user_id,
        user_name=target_user.name,
        user_phone=target_user.phone,
        user_role=target_user.role.value,
        department=staff.department,
        employee_id=staff.employee_id,
        shift=staff.shift,
        is_active=staff.is_active,
        created_at=staff.created_at,
    )


@router.get(
    "/{hospital_id}/staff",
    response_model=List[StaffOut],
    summary="List hospital staff",
)
async def list_staff(
    hospital_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all active staff at a hospital."""
    result = await db.execute(
        select(HospitalStaff).where(
            and_(
                HospitalStaff.hospital_id == hospital_id,
                HospitalStaff.is_active == True,
            )
        )
    )
    staff_list = result.scalars().all()

    out = []
    for s in staff_list:
        user_result = await db.execute(select(User).where(User.id == s.user_id))
        user = user_result.scalar_one()
        out.append(StaffOut(
            id=s.id,
            hospital_id=s.hospital_id,
            user_id=s.user_id,
            user_name=user.name,
            user_phone=user.phone,
            user_role=user.role.value,
            department=s.department,
            employee_id=s.employee_id,
            shift=s.shift,
            is_active=s.is_active,
            created_at=s.created_at,
        ))
    return out


@router.put(
    "/{hospital_id}/staff/{staff_id}",
    response_model=StaffOut,
    summary="Update staff member",
)
async def update_staff(
    hospital_id: UUID,
    staff_id: UUID,
    data: StaffUpdate,
    current_user: User = Depends(require_roles(UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    """Update staff details (department, shift, etc). Admin only."""
    result = await db.execute(
        select(HospitalStaff).where(
            and_(HospitalStaff.id == staff_id, HospitalStaff.hospital_id == hospital_id)
        )
    )
    staff = result.scalar_one_or_none()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(staff, key, value)

    await db.flush()
    await db.refresh(staff)

    user_result = await db.execute(select(User).where(User.id == staff.user_id))
    user = user_result.scalar_one()

    return StaffOut(
        id=staff.id,
        hospital_id=staff.hospital_id,
        user_id=staff.user_id,
        user_name=user.name,
        user_phone=user.phone,
        user_role=user.role.value,
        department=staff.department,
        employee_id=staff.employee_id,
        shift=staff.shift,
        is_active=staff.is_active,
        created_at=staff.created_at,
    )


@router.delete("/{hospital_id}/staff/{staff_id}", summary="Remove staff member")
async def remove_staff(
    hospital_id: UUID,
    staff_id: UUID,
    current_user: User = Depends(require_roles(UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a staff member. Admin only."""
    result = await db.execute(
        select(HospitalStaff).where(
            and_(HospitalStaff.id == staff_id, HospitalStaff.hospital_id == hospital_id)
        )
    )
    staff = result.scalar_one_or_none()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")

    staff.is_active = False
    return {"message": "Staff member deactivated"}


# ── Patient Assignments ──────────────────────────────────────

@router.post(
    "/{hospital_id}/assignments",
    response_model=AssignmentOut,
    status_code=201,
    summary="Assign patient to nurse",
)
async def create_assignment(
    hospital_id: UUID,
    data: AssignmentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Assign a patient to a nurse with ward/bed number. Staff only."""
    await _require_hospital_staff(hospital_id, current_user, db)

    # Verify nurse is staff at this hospital
    nurse_staff = await db.execute(
        select(HospitalStaff).where(
            and_(
                HospitalStaff.hospital_id == hospital_id,
                HospitalStaff.user_id == data.nurse_id,
                HospitalStaff.is_active == True,
            )
        )
    )
    if not nurse_staff.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Nurse is not active staff at this hospital")

    # Look up patient
    patient_result = await db.execute(select(User).where(User.phone == data.patient_phone))
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found with this phone number")

    # Check duplicate active assignment
    existing = await db.execute(
        select(PatientAssignment).where(
            and_(
                PatientAssignment.hospital_id == hospital_id,
                PatientAssignment.patient_id == patient.id,
                PatientAssignment.is_active == True,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Patient already has an active assignment at this hospital")

    assignment = PatientAssignment(
        hospital_id=hospital_id,
        nurse_id=data.nurse_id,
        patient_id=patient.id,
        ward=data.ward,
        bed_number=data.bed_number,
        admitted_date=data.admitted_date or date.today(),
    )
    db.add(assignment)
    await db.flush()
    await db.refresh(assignment)

    nurse_result = await db.execute(select(User).where(User.id == data.nurse_id))
    nurse = nurse_result.scalar_one()

    return AssignmentOut(
        id=assignment.id,
        hospital_id=assignment.hospital_id,
        nurse_id=assignment.nurse_id,
        nurse_name=nurse.name,
        patient_id=assignment.patient_id,
        patient_name=patient.name,
        patient_phone=patient.phone,
        ward=assignment.ward,
        bed_number=assignment.bed_number,
        admitted_date=assignment.admitted_date,
        discharged_date=assignment.discharged_date,
        is_active=assignment.is_active,
        created_at=assignment.created_at,
    )


@router.get(
    "/{hospital_id}/assignments",
    response_model=List[AssignmentOut],
    summary="List patient assignments",
)
async def list_assignments(
    hospital_id: UUID,
    nurse_id: Optional[UUID] = None,
    ward: Optional[str] = None,
    active_only: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List patient assignments. Filter by nurse or ward."""
    await _require_hospital_staff(hospital_id, current_user, db)

    query = select(PatientAssignment).where(PatientAssignment.hospital_id == hospital_id)
    if active_only:
        query = query.where(PatientAssignment.is_active == True)
    if nurse_id:
        query = query.where(PatientAssignment.nurse_id == nurse_id)
    if ward:
        query = query.where(PatientAssignment.ward == ward)
    query = query.order_by(PatientAssignment.ward, PatientAssignment.bed_number)

    result = await db.execute(query)
    assignments = result.scalars().all()

    out = []
    for a in assignments:
        nurse_result = await db.execute(select(User).where(User.id == a.nurse_id))
        nurse = nurse_result.scalar_one()
        patient_result = await db.execute(select(User).where(User.id == a.patient_id))
        patient = patient_result.scalar_one()

        out.append(AssignmentOut(
            id=a.id,
            hospital_id=a.hospital_id,
            nurse_id=a.nurse_id,
            nurse_name=nurse.name,
            patient_id=a.patient_id,
            patient_name=patient.name,
            patient_phone=patient.phone,
            ward=a.ward,
            bed_number=a.bed_number,
            admitted_date=a.admitted_date,
            discharged_date=a.discharged_date,
            is_active=a.is_active,
            created_at=a.created_at,
        ))
    return out


@router.put(
    "/{hospital_id}/assignments/{assignment_id}",
    response_model=AssignmentOut,
    summary="Update assignment",
)
async def update_assignment(
    hospital_id: UUID,
    assignment_id: UUID,
    data: AssignmentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update patient assignment (reassign nurse, change ward/bed, discharge)."""
    await _require_hospital_staff(hospital_id, current_user, db)

    result = await db.execute(
        select(PatientAssignment).where(
            and_(
                PatientAssignment.id == assignment_id,
                PatientAssignment.hospital_id == hospital_id,
            )
        )
    )
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(assignment, key, value)

    # Auto-deactivate on discharge
    if data.discharged_date is not None:
        assignment.is_active = False

    await db.flush()
    await db.refresh(assignment)

    nurse_result = await db.execute(select(User).where(User.id == assignment.nurse_id))
    nurse = nurse_result.scalar_one()
    patient_result = await db.execute(select(User).where(User.id == assignment.patient_id))
    patient = patient_result.scalar_one()

    return AssignmentOut(
        id=assignment.id,
        hospital_id=assignment.hospital_id,
        nurse_id=assignment.nurse_id,
        nurse_name=nurse.name,
        patient_id=assignment.patient_id,
        patient_name=patient.name,
        patient_phone=patient.phone,
        ward=assignment.ward,
        bed_number=assignment.bed_number,
        admitted_date=assignment.admitted_date,
        discharged_date=assignment.discharged_date,
        is_active=assignment.is_active,
        created_at=assignment.created_at,
    )


# ── Nurse Dashboard ──────────────────────────────────────────

@router.get(
    "/{hospital_id}/dashboard",
    response_model=List[NursePatientSchedule],
    summary="Nurse dashboard — assigned patients' schedules",
)
async def nurse_dashboard(
    hospital_id: UUID,
    target_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get medication schedules for all patients assigned to the current nurse.

    Returns each patient with their ward/bed and today's medication schedule.
    """
    staff = await _require_hospital_staff(hospital_id, current_user, db)

    check_date = target_date or date.today()

    # Get nurse's active patient assignments
    assignments_result = await db.execute(
        select(PatientAssignment).where(
            and_(
                PatientAssignment.hospital_id == hospital_id,
                PatientAssignment.nurse_id == current_user.id,
                PatientAssignment.is_active == True,
            )
        )
    )
    assignments = assignments_result.scalars().all()

    dashboard = []

    for assignment in assignments:
        # Get patient info
        patient_result = await db.execute(
            select(User).where(User.id == assignment.patient_id)
        )
        patient = patient_result.scalar_one()

        # Get patient's active medications
        meds_result = await db.execute(
            select(Medication).where(
                and_(
                    Medication.user_id == assignment.patient_id,
                    Medication.is_active == True,
                )
            ).order_by(Medication.exact_hour, Medication.exact_minute)
        )
        meds = meds_result.scalars().all()

        # Get today's dose logs
        logs_result = await db.execute(
            select(DoseLog).where(
                and_(
                    DoseLog.user_id == assignment.patient_id,
                    DoseLog.scheduled_date == check_date,
                )
            )
        )
        logs = {str(log.medication_id): log for log in logs_result.scalars().all()}

        # Build schedule
        now = datetime.now(timezone.utc)
        current_minutes = now.hour * 60 + now.minute
        schedule_items = []

        for med in meds:
            if not _is_due_on(med, check_date):
                continue

            dose_log = logs.get(str(med.id))
            med_minutes = (med.exact_hour or 0) * 60 + (med.exact_minute or 0)
            is_today = check_date == date.today()
            is_due = is_today and current_minutes >= med_minutes and current_minutes <= med_minutes + 30 and not dose_log
            is_missed = is_today and current_minutes > med_minutes + 60 and not dose_log

            item = {
                "medication": MedicationOut.model_validate(med).model_dump(),
                "dose_log": DoseLogOut.model_validate(dose_log).model_dump() if dose_log else None,
                "is_due": is_due,
                "is_missed": is_missed,
            }
            schedule_items.append(item)

        dashboard.append(NursePatientSchedule(
            patient_id=patient.id,
            patient_name=patient.name,
            ward=assignment.ward,
            bed_number=assignment.bed_number,
            medications=schedule_items,
        ))

    return dashboard


# ── Nurse Dose Administration ────────────────────────────────

INJ_SITES = ["Left Arm", "Right Arm", "Left Thigh", "Right Thigh", "Abdomen Left", "Abdomen Right"]


@router.post(
    "/{hospital_id}/administer/{med_id}",
    summary="Nurse administers dose",
)
async def nurse_administer_dose(
    hospital_id: UUID,
    med_id: UUID,
    notes: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Nurse logs a dose as administered for an assigned patient.

    Same as mark_taken but verified that the nurse is assigned to this patient.
    """
    await _require_hospital_staff(hospital_id, current_user, db)

    # Get medication
    med_result = await db.execute(select(Medication).where(Medication.id == med_id))
    med = med_result.scalar_one_or_none()
    if not med:
        raise HTTPException(status_code=404, detail="Medication not found")

    # Verify nurse is assigned to this patient
    assignment = await db.execute(
        select(PatientAssignment).where(
            and_(
                PatientAssignment.hospital_id == hospital_id,
                PatientAssignment.nurse_id == current_user.id,
                PatientAssignment.patient_id == med.user_id,
                PatientAssignment.is_active == True,
            )
        )
    )
    if not assignment.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not assigned to this patient")

    today = date.today()
    now = datetime.now(timezone.utc)

    # Check duplicate
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
        raise HTTPException(status_code=409, detail="Dose already administered today")

    # Injection site rotation
    inj_site = None
    if med.form and med.form.value == "injection":
        idx = med.injection_site_index or 0
        inj_site = INJ_SITES[idx % len(INJ_SITES)]
        med.injection_site_index = (idx + 1) % len(INJ_SITES)

    # Decrement stock
    if med.stock_quantity and med.stock_quantity > 0:
        med.stock_quantity -= 1

    # Create dose log with nurse as logger
    log = DoseLog(
        medication_id=med.id,
        user_id=med.user_id,
        scheduled_date=today,
        scheduled_time=time(med.exact_hour or 0, med.exact_minute or 0) if med.exact_hour is not None else None,
        status=DoseStatus.taken,
        actual_time=now,
        logged_by=current_user.id,
        injection_site=inj_site,
        notes=f"[Administered by {current_user.name}]" + (f" {notes}" if notes else ""),
    )
    db.add(log)
    await db.flush()
    await db.refresh(log)

    return {
        "message": "Dose administered",
        "dose_log_id": str(log.id),
        "medication": med.name,
        "patient_id": str(med.user_id),
        "administered_by": current_user.name,
        "injection_site": inj_site,
    }
