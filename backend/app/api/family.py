"""Family API — CRUD for families, member management, caregiver permissions."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.family import Family, FamilyMember
from app.models.user import User, UserRole
from app.schemas.family import (
    FamilyCreate,
    FamilyMemberAdd,
    FamilyMemberOut,
    FamilyMemberUpdate,
    FamilyOut,
)
from app.utils.auth import get_current_user

router = APIRouter(prefix="/families", tags=["Family & Caregivers"])


# ── Caregiver: linked patients (must be before /{family_id} routes) ──

@router.get("/linked-patients", response_model=List[FamilyMemberOut], summary="My linked patients")
async def linked_patients(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all family members the current user can manage (has can_edit access to)."""
    # Find all families current user belongs to with can_edit
    my_families = select(FamilyMember.family_id).where(
        and_(
            FamilyMember.user_id == current_user.id,
            FamilyMember.can_edit == True,
        )
    ).scalar_subquery()

    # Get all other members of those families
    result = await db.execute(
        select(FamilyMember)
        .where(
            and_(
                FamilyMember.family_id.in_(my_families),
                FamilyMember.user_id != current_user.id,
            )
        )
    )
    members = result.scalars().all()

    out = []
    for m in members:
        user_result = await db.execute(select(User).where(User.id == m.user_id))
        member_user = user_result.scalar_one()
        out.append(FamilyMemberOut(
            id=m.id,
            user_id=m.user_id,
            user_name=member_user.name,
            user_phone=member_user.phone,
            relationship=m.relation_type,
            nickname=m.nickname,
            can_edit=m.can_edit,
            receives_sos=m.receives_sos,
            receives_missed_alerts=m.receives_missed_alerts,
            created_at=m.created_at,
        ))
    return out


# ── Family CRUD ──────────────────────────────────────────────

@router.post("", response_model=FamilyOut, status_code=201, summary="Create family")
async def create_family(
    data: FamilyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new family group. Creator is automatically added as a member."""
    family = Family(name=data.name, created_by=current_user.id)
    db.add(family)
    await db.flush()

    # Auto-add creator as a member with full permissions
    creator_member = FamilyMember(
        family_id=family.id,
        user_id=current_user.id,
        relation_type="self",
        nickname=current_user.name,
        can_edit=True,
        receives_sos=True,
        receives_missed_alerts=True,
        added_by=current_user.id,
    )
    db.add(creator_member)
    await db.flush()

    # Reload with members
    result = await db.execute(
        select(Family)
        .where(Family.id == family.id)
        .options(selectinload(Family.members))
    )
    family = result.scalar_one()
    return _family_to_out(family)


@router.get("", response_model=List[FamilyOut], summary="List my families")
async def list_families(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all families the current user belongs to."""
    # Find family IDs where user is a member
    member_families = select(FamilyMember.family_id).where(
        FamilyMember.user_id == current_user.id
    ).scalar_subquery()

    result = await db.execute(
        select(Family)
        .where(Family.id.in_(member_families))
        .options(selectinload(Family.members))
        .order_by(Family.created_at.desc())
    )
    families = result.scalars().unique().all()
    return [_family_to_out(f) for f in families]


@router.get("/{family_id}", response_model=FamilyOut, summary="Get family details")
async def get_family(
    family_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get family details with all members. Must be a member."""
    family = await _get_family_or_404(family_id, db)
    _require_membership(family, current_user)
    return _family_to_out(family)


@router.put("/{family_id}", response_model=FamilyOut, summary="Update family")
async def update_family(
    family_id: UUID,
    data: FamilyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update family name. Only creator or admin can update."""
    family = await _get_family_or_404(family_id, db)
    if family.created_by != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Only family creator can update")

    family.name = data.name
    await db.flush()
    await db.refresh(family)

    # Reload with members
    result = await db.execute(
        select(Family)
        .where(Family.id == family.id)
        .options(selectinload(Family.members))
    )
    family = result.scalar_one()
    return _family_to_out(family)


@router.delete("/{family_id}", summary="Delete family")
async def delete_family(
    family_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete family. Only creator or admin can delete."""
    family = await _get_family_or_404(family_id, db)
    if family.created_by != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Only family creator can delete")

    await db.delete(family)
    return {"message": "Family deleted"}


# ── Member Management ────────────────────────────────────────

@router.post(
    "/{family_id}/members",
    response_model=FamilyMemberOut,
    status_code=201,
    summary="Add family member",
)
async def add_member(
    family_id: UUID,
    data: FamilyMemberAdd,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a user to the family by phone number. User must already exist."""
    family = await _get_family_or_404(family_id, db)
    _require_membership(family, current_user)

    # Look up user by phone
    result = await db.execute(select(User).where(User.phone == data.phone))
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found with this phone number")

    # Check if already a member
    existing = await db.execute(
        select(FamilyMember).where(
            and_(
                FamilyMember.family_id == family_id,
                FamilyMember.user_id == target_user.id,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="User is already a member of this family")

    member = FamilyMember(
        family_id=family_id,
        user_id=target_user.id,
        relation_type=data.relationship,
        nickname=data.nickname,
        can_edit=data.can_edit,
        receives_sos=data.receives_sos,
        receives_missed_alerts=data.receives_missed_alerts,
        added_by=current_user.id,
    )
    db.add(member)
    await db.flush()
    await db.refresh(member)

    return FamilyMemberOut(
        id=member.id,
        user_id=member.user_id,
        user_name=target_user.name,
        user_phone=target_user.phone,
        relationship=member.relation_type,
        nickname=member.nickname,
        can_edit=member.can_edit,
        receives_sos=member.receives_sos,
        receives_missed_alerts=member.receives_missed_alerts,
        created_at=member.created_at,
    )


@router.put(
    "/{family_id}/members/{member_id}",
    response_model=FamilyMemberOut,
    summary="Update member permissions",
)
async def update_member(
    family_id: UUID,
    member_id: UUID,
    data: FamilyMemberUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a family member's permissions or relationship. Creator or admin only."""
    family = await _get_family_or_404(family_id, db)
    if family.created_by != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Only family creator can update members")

    result = await db.execute(
        select(FamilyMember).where(
            and_(FamilyMember.id == member_id, FamilyMember.family_id == family_id)
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Family member not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        if key == "relationship":
            setattr(member, "relation_type", value)
        else:
            setattr(member, key, value)

    await db.flush()
    await db.refresh(member)

    # Fetch user info for response
    user_result = await db.execute(select(User).where(User.id == member.user_id))
    member_user = user_result.scalar_one()

    return FamilyMemberOut(
        id=member.id,
        user_id=member.user_id,
        user_name=member_user.name,
        user_phone=member_user.phone,
        relationship=member.relation_type,
        nickname=member.nickname,
        can_edit=member.can_edit,
        receives_sos=member.receives_sos,
        receives_missed_alerts=member.receives_missed_alerts,
        created_at=member.created_at,
    )


@router.delete("/{family_id}/members/{member_id}", summary="Remove family member")
async def remove_member(
    family_id: UUID,
    member_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a member from the family. Creator, admin, or self-removal."""
    family = await _get_family_or_404(family_id, db)

    result = await db.execute(
        select(FamilyMember).where(
            and_(FamilyMember.id == member_id, FamilyMember.family_id == family_id)
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Family member not found")

    # Allow: creator, admin, or self-removal
    is_creator = family.created_by == current_user.id
    is_admin = current_user.role == UserRole.admin
    is_self = member.user_id == current_user.id

    if not (is_creator or is_admin or is_self):
        raise HTTPException(status_code=403, detail="Not authorized to remove this member")

    await db.delete(member)
    return {"message": "Member removed from family"}


# ── Helpers ──────────────────────────────────────────────────

async def _get_family_or_404(family_id: UUID, db: AsyncSession) -> Family:
    """Fetch family with members or raise 404."""
    result = await db.execute(
        select(Family)
        .where(Family.id == family_id)
        .options(selectinload(Family.members))
    )
    family = result.scalar_one_or_none()
    if not family:
        raise HTTPException(status_code=404, detail="Family not found")
    return family


def _require_membership(family: Family, user: User) -> None:
    """Raise 403 if user is not a member of this family (admins bypass)."""
    if user.role == UserRole.admin:
        return
    member_ids = [m.user_id for m in family.members]
    if user.id not in member_ids:
        raise HTTPException(status_code=403, detail="Not a member of this family")


def _family_to_out(family: Family) -> FamilyOut:
    """Convert Family ORM to FamilyOut schema, resolving user info from members."""
    members_out = []
    for m in family.members:
        # Access eagerly-loaded user relationship
        user = m.user if hasattr(m, "user") and m.user else None
        members_out.append(FamilyMemberOut(
            id=m.id,
            user_id=m.user_id,
            user_name=user.name if user else None,
            user_phone=user.phone if user else None,
            relationship=m.relation_type,
            nickname=m.nickname,
            can_edit=m.can_edit,
            receives_sos=m.receives_sos,
            receives_missed_alerts=m.receives_missed_alerts,
            created_at=m.created_at,
        ))
    return FamilyOut(
        id=family.id,
        name=family.name,
        created_by=family.created_by,
        members=members_out,
        created_at=family.created_at,
    )
