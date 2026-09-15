from app.age import age_from_dob, is_minor
from app.comparison import conflict_severity
from app.models import (
    AccessRequest,
    CorrectionSuggestion,
    Diagnosis,
    Doctor,
    Flag,
    Notification,
    Patient,
    Surrogate,
    User,
)


def user_public(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "date_of_birth": user.date_of_birth.isoformat(),
        "age": age_from_dob(user.date_of_birth),
        "is_minor": is_minor(user.date_of_birth),
    }


def patient_record(patient: Patient, access_status: str | None = None) -> dict:
    user = patient.user
    surrogate = patient.surrogate
    return {
        "id": patient.id,
        "user_id": patient.user_id,
        "name": user.name,
        "email": user.email,
        "date_of_birth": user.date_of_birth.isoformat(),
        "age": age_from_dob(user.date_of_birth),
        "is_minor": is_minor(user.date_of_birth),
        "conditions": patient.conditions or [],
        "medications": patient.medications or [],
        "surrogate_id": patient.surrogate_id,
        "surrogate_name": surrogate.user.name if surrogate else None,
        "surrogate_relationship": surrogate.relationship if surrogate else None,
        "access_status": access_status,
    }


def doctor_public(doctor: Doctor) -> dict:
    return {
        "id": doctor.id,
        "name": doctor.user.name,
        "specialty": doctor.specialty,
        "hospital": doctor.hospital,
        "email": doctor.user.email,
    }


def diagnosis_public(dx: Diagnosis, *, include_notes: bool, include_label: bool) -> dict:
    payload = {
        "id": dx.id,
        "patient_id": dx.patient_id,
        "doctor": doctor_public(dx.doctor),
        "timestamp": dx.timestamp.isoformat() if dx.timestamp else None,
        "disclose_to_patient": dx.disclose_to_patient,
        "disclosure_reason": dx.disclosure_reason,
    }
    if include_label:
        payload["diagnosis_label"] = dx.diagnosis_label
    else:
        payload["diagnosis_label"] = None
    if include_notes:
        payload["full_notes"] = dx.full_notes
    else:
        payload["full_notes"] = None
    return payload


def flag_public(flag: Flag, *, viewer_role: str, reveal_detail: bool) -> dict:
    show = reveal_detail
    severity = flag.severity or conflict_severity(
        flag.diagnosis_1.diagnosis_label,
        flag.diagnosis_2.diagnosis_label,
    )
    return {
        "id": flag.id,
        "patient_id": flag.patient_id,
        "patient_name": flag.patient.user.name,
        "status": flag.status,
        "severity": severity,
        "root_cause": flag.root_cause or "Label mismatch",
        "resolution_note": flag.resolution_note if show and flag.status == "resolved" else None,
        "diagnosis_1": diagnosis_public(
            flag.diagnosis_1,
            include_notes=show,
            include_label=show or viewer_role == "doctor",
        ),
        "diagnosis_2": diagnosis_public(
            flag.diagnosis_2,
            include_notes=show,
            include_label=show or viewer_role == "doctor",
        ),
        "pending_review": flag.status != "resolved" and viewer_role != "doctor",
    }


def notification_public(note: Notification) -> dict:
    return {
        "id": note.id,
        "type": note.type,
        "message": note.message,
        "related_id": note.related_id,
        "read": note.read,
        "timestamp": note.timestamp.isoformat() if note.timestamp else None,
    }


def access_public(req: AccessRequest) -> dict:
    return {
        "id": req.id,
        "status": req.status,
        "timestamp": req.timestamp.isoformat() if req.timestamp else None,
        "doctor": doctor_public(req.doctor),
        "patient": {
            "id": req.patient.id,
            "name": req.patient.user.name,
            "is_minor": is_minor(req.patient.user.date_of_birth),
        },
    }


def correction_public(item: CorrectionSuggestion) -> dict:
    return {
        "id": item.id,
        "patient_id": item.patient_id,
        "field": item.field,
        "proposed_value": item.proposed_value,
        "status": item.status,
        "timestamp": item.timestamp.isoformat() if item.timestamp else None,
        "submitted_by": item.submitted_by.name,
    }


def me_payload(user: User, patient: Patient | None, surrogate: Surrogate | None) -> dict:
    payload = {
        "user": user_public(user),
        "doctor": doctor_public(user.doctor) if user.doctor else None,
        "patient": patient_record(patient) if patient and user.role == "patient" else None,
        "surrogate": None,
    }
    if surrogate:
        linked = surrogate.linked_patient
        payload["surrogate"] = {
            "id": surrogate.id,
            "relationship": surrogate.relationship,
            "linked_patient": patient_record(linked),
        }
    return payload
