from datetime import datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship as orm_relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    username: Mapped[str | None] = mapped_column(String(80), unique=True, nullable=True)
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
    medical_reports: Mapped[list["MedicalReport"]] = orm_relationship(back_populates="patient")
    conversations: Mapped[list["DoctorConversation"]] = orm_relationship(back_populates="patient")


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    specialty: Mapped[str] = mapped_column(String(120), nullable=False)
    hospital: Mapped[str] = mapped_column(String(120), nullable=False)
    qualification_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    years_experience: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    research_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    resolved_cases_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # credibility_score only ever increases (via resolved_cases_count). Never decrement for declines.
    credibility_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    user: Mapped[User] = orm_relationship(back_populates="doctor")
    diagnoses: Mapped[list["Diagnosis"]] = orm_relationship(back_populates="doctor")
    access_requests: Mapped[list["AccessRequest"]] = orm_relationship(back_populates="doctor")
    medical_reports: Mapped[list["MedicalReport"]] = orm_relationship(back_populates="doctor")


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
    ai_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution_deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    assigned_doctor_id: Mapped[int | None] = mapped_column(ForeignKey("doctors.id"), nullable=True)
    judge_pool_open: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    patient_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    gap_answer: Mapped[str | None] = mapped_column(String(32), nullable=True)
    gap_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    patient: Mapped[Patient] = orm_relationship(back_populates="flags")
    diagnosis_1: Mapped[Diagnosis] = orm_relationship(foreign_keys=[diagnosis_id_1])
    diagnosis_2: Mapped[Diagnosis] = orm_relationship(foreign_keys=[diagnosis_id_2])
    assigned_doctor: Mapped["Doctor | None"] = orm_relationship(foreign_keys=[assigned_doctor_id])
    judge_declines: Mapped[list["JudgeDecline"]] = orm_relationship(back_populates="flag")
    guest_invites: Mapped[list["GuestJudgeInvite"]] = orm_relationship(back_populates="flag")


class JudgeDecline(Base):
    """Analytics-only record that a doctor declined to judge a flag.

    Declining must never change credibility_score. This table exists so we can
    count non-participation without attaching any penalty to it.
    """

    __tablename__ = "judge_declines"
    __table_args__ = (UniqueConstraint("flag_id", "doctor_id", name="uq_judge_decline_flag_doctor"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    flag_id: Mapped[int] = mapped_column(ForeignKey("flags.id"), nullable=False)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    flag: Mapped["Flag"] = orm_relationship(back_populates="judge_declines")
    doctor: Mapped["Doctor"] = orm_relationship()


class GuestJudgeInvite(Base):
    """One-flag guest access for an external doctor. No Hetu account is created."""

    __tablename__ = "guest_judge_invites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    flag_id: Mapped[int] = mapped_column(ForeignKey("flags.id"), nullable=False)
    invited_name: Mapped[str] = mapped_column(String(120), nullable=False)
    invited_email: Mapped[str] = mapped_column(String(255), nullable=False)
    invited_specialty: Mapped[str] = mapped_column(String(120), nullable=False)
    license_number: Mapped[str] = mapped_column(String(80), nullable=False)
    invite_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="invited", nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    judgment_choice: Mapped[str | None] = mapped_column(String(32), nullable=True)
    judgment_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    invited_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    flag: Mapped["Flag"] = orm_relationship(back_populates="guest_invites")
    invited_by: Mapped["User"] = orm_relationship()


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


class MedicalReport(Base):
    """Report event. Typed notes plus an optional stored file."""

    __tablename__ = "medical_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    doctor_id: Mapped[int | None] = mapped_column(ForeignKey("doctors.id"), nullable=True)
    submitted_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    related_issue: Mapped[str] = mapped_column(String(160), nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="typed", nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    report_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    patient: Mapped[Patient] = orm_relationship(back_populates="medical_reports")
    doctor: Mapped["Doctor | None"] = orm_relationship(back_populates="medical_reports")
    submitted_by: Mapped["User | None"] = orm_relationship(foreign_keys=[submitted_by_user_id])


class DoctorConversation(Base):
    __tablename__ = "doctor_conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    doctor_id_1: Mapped[int] = mapped_column(ForeignKey("doctors.id"), nullable=False)
    doctor_id_2: Mapped[int] = mapped_column(ForeignKey("doctors.id"), nullable=False)
    report_id_1: Mapped[int] = mapped_column(ForeignKey("medical_reports.id"), nullable=False)
    report_id_2: Mapped[int] = mapped_column(ForeignKey("medical_reports.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending_schedule", nullable=False)
    scheduled_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    schedule_deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    transcript_or_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    senior_doctor_id: Mapped[int | None] = mapped_column(ForeignKey("doctors.id"), nullable=True)
    issue_type: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    agreed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    conclusion: Mapped[str | None] = mapped_column(Text, nullable=True)
    patient_conclusion: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    patient: Mapped[Patient] = orm_relationship(back_populates="conversations")
    doctor_1: Mapped[Doctor] = orm_relationship(foreign_keys=[doctor_id_1])
    doctor_2: Mapped[Doctor] = orm_relationship(foreign_keys=[doctor_id_2])
    senior_doctor: Mapped["Doctor | None"] = orm_relationship(foreign_keys=[senior_doctor_id])
    report_1: Mapped[MedicalReport] = orm_relationship(foreign_keys=[report_id_1])
    report_2: Mapped[MedicalReport] = orm_relationship(foreign_keys=[report_id_2])
    notes: Mapped[list["ConversationNote"]] = orm_relationship(back_populates="conversation")
    availabilities: Mapped[list["DoctorAvailability"]] = orm_relationship(back_populates="conversation")


class ConversationNote(Base):
    __tablename__ = "conversation_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("doctor_conversations.id"), nullable=False)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    conversation: Mapped[DoctorConversation] = orm_relationship(back_populates="notes")
    doctor: Mapped[Doctor] = orm_relationship()


class DoctorAvailability(Base):
    __tablename__ = "doctor_availabilities"
    __table_args__ = (UniqueConstraint("conversation_id", "doctor_id", name="uq_availability_conversation_doctor"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("doctor_conversations.id"), nullable=False)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), nullable=False)
    slots: Mapped[list] = mapped_column(JSON, default=list)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    conversation: Mapped[DoctorConversation] = orm_relationship(back_populates="availabilities")
    doctor: Mapped[Doctor] = orm_relationship()
