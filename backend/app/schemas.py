from datetime import date

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    password: str
    email: str = ""
    username: str = ""
    identifier: str = ""


class SignupRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=120)
    confirm_password: str = Field(min_length=8, max_length=120)
    age: int = Field(ge=1, le=120)
    role: str
    linked_patient_email: str | None = None
    specialty: str | None = None
    hospital: str | None = None
    years_experience: int = 0


class ResolveFlagRequest(BaseModel):
    resolution_note: str = Field(min_length=3)


class GuestJudgeInviteRequest(BaseModel):
    invited_name: str = Field(min_length=2, max_length=120)
    invited_email: str = Field(min_length=5, max_length=255)
    invited_specialty: str = Field(min_length=2, max_length=120)
    license_number: str = Field(min_length=6, max_length=80)


class GuestLicenseRequest(BaseModel):
    license_number: str = Field(min_length=6, max_length=80)


class GuestJudgmentRequest(BaseModel):
    choice: str = Field(min_length=3, max_length=32)
    explanation: str = Field(min_length=3)


class DoctorSignupRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=120)
    specialty: str = Field(min_length=2, max_length=120)
    hospital: str = Field(default="Independent practice", max_length=120)
    license_number: str = Field(min_length=6, max_length=80)
    date_of_birth: date
    qualification_score: float = 0
    years_experience: int = 0
    research_count: int = 0
    prefill_token: str | None = None


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


class GapResponseRequest(BaseModel):
    answer: str = Field(min_length=2, max_length=16)
    detail: str = ""


class AvailabilityRequest(BaseModel):
    slots: list[str] = Field(min_length=1)


class ConversationNoteRequest(BaseModel):
    body: str = Field(min_length=1)


class ConversationCompleteRequest(BaseModel):
    conclusion: str = Field(min_length=3)
    agreed: bool
    good_treatment: bool = True


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
