from datetime import datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship as orm_relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    date_of_birth: Mapped[datetime] = mapped_column(Date, nullable=False)

    patient: Mapped["Patient | None"] = orm_relationship(back_populates="user", uselist=False)
    doctor: Mapped["Doctor | None"] = orm_relationship(back_populates="user", uselist=False)
    surrogate: Mapped["Surrogate | None"] = orm_relationship(back_populates="user", uselist=False)
    notifications: Mapped[list["Notification"]] = orm_relationship(back_populates="user")


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    surrogate_id: Mapped[int | None] = mapped_column(ForeignKey("surrogates.id"), nullable=True)
    conditions: Mapped[list] = mapped_column(JSON, default=list)
    medications: Mapped[list] = mapped_column(JSON, default=list)

    user: Mapped[User] = orm_relationship(back_populates="patient")
    surrogate: Mapped["Surrogate | None"] = orm_relationship(
        foreign_keys=[surrogate_id],
    )
    diagnoses: Mapped[list["Diagnosis"]] = orm_relationship(back_populates="patient")
    flags: Mapped[list["Flag"]] = orm_relationship(back_populates="patient")
    access_requests: Mapped[list["AccessRequest"]] = orm_relationship(back_populates="patient")
    corrections: Mapped[list["CorrectionSuggestion"]] = orm_relationship(back_populates="patient")


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    specialty: Mapped[str] = mapped_column(String(120), nullable=False)
    hospital: Mapped[str] = mapped_column(String(120), nullable=False)

    user: Mapped[User] = orm_relationship(back_populates="doctor")
    diagnoses: Mapped[list["Diagnosis"]] = orm_relationship(back_populates="doctor")
    access_requests: Mapped[list["AccessRequest"]] = orm_relationship(back_populates="doctor")


class Surrogate(Base):
    __tablename__ = "surrogates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    linked_patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    relationship: Mapped[str] = mapped_column(String(80), nullable=False)

    user: Mapped[User] = orm_relationship(back_populates="surrogate")
    linked_patient: Mapped[Patient] = orm_relationship(foreign_keys=[linked_patient_id])


class AccessRequest(Base):
    __tablename__ = "access_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), nullable=False)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    doctor: Mapped[Doctor] = orm_relationship(back_populates="access_requests")
    patient: Mapped[Patient] = orm_relationship(back_populates="access_requests")


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), nullable=False)
    diagnosis_label: Mapped[str] = mapped_column(String(160), nullable=False)
    full_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    disclose_to_patient: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclosure_reason: Mapped[str | None] = mapped_column(String(160), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    patient: Mapped[Patient] = orm_relationship(back_populates="diagnoses")
    doctor: Mapped[Doctor] = orm_relationship(back_populates="diagnoses")


class Flag(Base):
    __tablename__ = "flags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    diagnosis_id_1: Mapped[int] = mapped_column(ForeignKey("diagnoses.id"), nullable=False)
    diagnosis_id_2: Mapped[int] = mapped_column(ForeignKey("diagnoses.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(16), default="high", nullable=False)
    root_cause: Mapped[str] = mapped_column(String(80), default="Label mismatch", nullable=False)

    patient: Mapped[Patient] = orm_relationship(back_populates="flags")
    diagnosis_1: Mapped[Diagnosis] = orm_relationship(foreign_keys=[diagnosis_id_1])
    diagnosis_2: Mapped[Diagnosis] = orm_relationship(foreign_keys=[diagnosis_id_2])


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    related_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    user: Mapped[User] = orm_relationship(back_populates="notifications")


class CorrectionSuggestion(Base):
    __tablename__ = "correction_suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    submitted_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    field: Mapped[str] = mapped_column(String(64), nullable=False)
    proposed_value: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    patient: Mapped[Patient] = orm_relationship(back_populates="corrections")
    submitted_by: Mapped[User] = orm_relationship()
