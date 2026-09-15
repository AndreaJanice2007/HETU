from datetime import date

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str
    password: str


class ResolveFlagRequest(BaseModel):
    resolution_note: str = Field(min_length=3)


class AccessCreateRequest(BaseModel):
    patient_id: int


class DiagnosisCreateRequest(BaseModel):
    patient_id: int
    diagnosis_label: str
    full_notes: str = ""
    disclose_to_patient: bool = True
    disclosure_reason: str | None = None


class CorrectionCreateRequest(BaseModel):
    patient_id: int
    field: str
    proposed_value: str


class MedreaChatRequest(BaseModel):
    messages: list[dict] = []
    report: dict | None = None


class UserPublic(BaseModel):
    id: int
    name: str
    email: str
    role: str
    date_of_birth: date
    age: int
    is_minor: bool


class DoctorPublic(BaseModel):
    id: int
    specialty: str
    hospital: str
    name: str


class PatientRecord(BaseModel):
    id: int
    user_id: int
    name: str
    email: str
    date_of_birth: date
    age: int
    is_minor: bool
    conditions: list
    medications: list
    surrogate_id: int | None
    surrogate_name: str | None = None
    surrogate_relationship: str | None = None
    access_status: str | None = None


class MeResponse(BaseModel):
    user: UserPublic
    doctor: dict | None = None
    patient: dict | None = None
    surrogate: dict | None = None
