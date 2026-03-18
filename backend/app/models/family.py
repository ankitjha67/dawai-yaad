"""Family model — supports multi-member families with Indian relationship context."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


# Indian family relationship choices (used in API validation, not DB enum)
RELATIONSHIP_CHOICES = [
    "father", "mother", "grandfather_paternal", "grandmother_paternal",
    "grandfather_maternal", "grandmother_maternal",
    "uncle_paternal", "aunt_paternal",  # chacha/chachi, tau/tai
    "uncle_maternal", "aunt_maternal",  # mama/mami, mausa/mausi
    "brother", "sister", "son", "daughter",
    "spouse", "in_law", "cousin", "friend", "neighbor", "other",
]


class Family(Base):
    __tablename__ = "families"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    members = relationship("FamilyMember", back_populates="family", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<Family {self.name}>"


class FamilyMember(Base):
    __tablename__ = "family_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    family_id = Column(UUID(as_uuid=True), ForeignKey("families.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    relation_type = Column(String(50), nullable=False)  # from RELATIONSHIP_CHOICES
    nickname = Column(String(100), nullable=True)  # "Dadi", "Nana", "Bua" etc.
    can_edit = Column(Boolean, default=False)
    receives_sos = Column(Boolean, default=True)
    receives_missed_alerts = Column(Boolean, default=True)
    added_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    family = relationship("Family", back_populates="members")
    user = relationship("User", foreign_keys=[user_id])
    adder = relationship("User", foreign_keys=[added_by])

    def __repr__(self):
        return f"<FamilyMember {self.relation_type}>"
