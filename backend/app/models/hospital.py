"""Hospital models — hospital registration, staff, patient assignments."""

import uuid
from datetime import datetime, date

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Hospital(Base):
    __tablename__ = "hospitals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    phone = Column(String(15), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    staff = relationship("HospitalStaff", back_populates="hospital", cascade="all, delete-orphan")
    assignments = relationship("PatientAssignment", back_populates="hospital", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Hospital {self.name}>"


class HospitalStaff(Base):
    __tablename__ = "hospital_staff"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey("hospitals.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    department = Column(String(100), nullable=True)
    employee_id = Column(String(50), nullable=True)
    shift = Column(String(20), nullable=True)  # morning, evening, night
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    hospital = relationship("Hospital", back_populates="staff")
    user = relationship("User", foreign_keys=[user_id])


class PatientAssignment(Base):
    __tablename__ = "patient_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey("hospitals.id"), nullable=False)
    nurse_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    ward = Column(String(50), nullable=True)
    bed_number = Column(String(20), nullable=True)
    admitted_date = Column(Date, nullable=True)
    discharged_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    hospital = relationship("Hospital", back_populates="assignments")
    nurse = relationship("User", foreign_keys=[nurse_id])
    patient = relationship("User", foreign_keys=[patient_id])
