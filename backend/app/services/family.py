"""Family permission service — checks family membership and caregiver access."""

from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.family import FamilyMember
from app.models.user import User, UserRole
from app.utils.auth import get_current_user


async def get_family_link(
    current_user_id: UUID,
    target_user_id: UUID,
    db: AsyncSession,
) -> FamilyMember | None:
    """Find the FamilyMember row linking current_user to target_user's family.

    Returns the FamilyMember row for current_user if both users share a family,
    or None if they are not in the same family.
    """
    # Find families the target user belongs to
    target_families = select(FamilyMember.family_id).where(
        FamilyMember.user_id == target_user_id
    ).scalar_subquery()

    # Check if current user is in any of those families
    result = await db.execute(
        select(FamilyMember).where(
            and_(
                FamilyMember.user_id == current_user_id,
                FamilyMember.family_id.in_(target_families),
            )
        )
    )
    return result.scalar_one_or_none()


async def check_view_access(
    current_user: User,
    target_user_id: UUID,
    db: AsyncSession,
) -> None:
    """Raise 403 if current_user cannot view target_user's data.

    Rules:
    - Users can always view their own data
    - Admins can view anyone
    - Family members can view each other
    """
    if current_user.id == target_user_id:
        return
    if current_user.role == UserRole.admin:
        return

    link = await get_family_link(current_user.id, target_user_id, db)
    if not link:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user's data",
        )


async def check_edit_access(
    current_user: User,
    target_user_id: UUID,
    db: AsyncSession,
) -> None:
    """Raise 403 if current_user cannot edit target_user's medications/data.

    Rules:
    - Users can always edit their own data
    - Admins can edit anyone
    - Family members with can_edit=True can edit
    """
    if current_user.id == target_user_id:
        return
    if current_user.role == UserRole.admin:
        return

    link = await get_family_link(current_user.id, target_user_id, db)
    if not link or not link.can_edit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to edit this user's data",
        )


async def get_family_member_ids(user_id: UUID, db: AsyncSession) -> list[UUID]:
    """Get all user_ids that share a family with given user (including self)."""
    # Find all families the user belongs to
    user_families = select(FamilyMember.family_id).where(
        FamilyMember.user_id == user_id
    ).scalar_subquery()

    # Get all members of those families
    result = await db.execute(
        select(FamilyMember.user_id).where(
            FamilyMember.family_id.in_(user_families)
        ).distinct()
    )
    member_ids = [row[0] for row in result.all()]

    # Always include self
    if user_id not in member_ids:
        member_ids.append(user_id)

    return member_ids


async def get_sos_recipient_ids(user_id: UUID, db: AsyncSession) -> list[UUID]:
    """Get user_ids of family members who receive SOS alerts for given user."""
    user_families = select(FamilyMember.family_id).where(
        FamilyMember.user_id == user_id
    ).scalar_subquery()

    result = await db.execute(
        select(FamilyMember.user_id).where(
            and_(
                FamilyMember.family_id.in_(user_families),
                FamilyMember.receives_sos == True,
                FamilyMember.user_id != user_id,
            )
        ).distinct()
    )
    return [row[0] for row in result.all()]
