from pathlib import Path

from app.age import age_from_dob, is_minor
from app.comparison import conflict_severity
from app.models import (
    AccessRequest,
    ConversationNote,
    CorrectionSuggestion,
    Diagnosis,
    Doctor,
    DoctorConversation,
    Flag,
    GuestJudgeInvite,
    MedicalReport,
    Notification,
    Patient,
    Surrogate,
    User,
)
from logic.patient_copy import (
    conversation_patient_status,
    ensure_patient_explanation,
    patient_next_step,
    patient_status_label,
)


def user_public(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "username": getattr(user, "username", None),
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
        "username": getattr(user, "username", None),
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
        "qualification_score": getattr(doctor, "qualification_score", 0) or 0,
        "years_experience": getattr(doctor, "years_experience", 0) or 0,
        "research_count": getattr(doctor, "research_count", 0) or 0,
        "resolved_cases_count": getattr(doctor, "resolved_cases_count", 0) or 0,
        "credibility_score": getattr(doctor, "credibility_score", 0) or 0,
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
    patient_view = viewer_role in {"patient", "surrogate"}
    show_labels = show or viewer_role == "doctor" or patient_view
    severity = flag.severity or conflict_severity(
        flag.diagnosis_1.diagnosis_label,
        flag.diagnosis_2.diagnosis_label,
    )
    explanation = ensure_patient_explanation(flag) if patient_view else None
    payload = {
        "id": flag.id,
        "patient_id": flag.patient_id,
        "patient_name": flag.patient.user.name,
        "status": flag.status,
        "severity": None if patient_view else severity,
        "root_cause": flag.root_cause or "Label mismatch",
        "ai_reasoning": None if patient_view else (flag.ai_reasoning if show or viewer_role == "doctor" else None),
        "patient_explanation": explanation,
        "patient_status_label": patient_status_label(severity, flag.status) if patient_view else None,
        "patient_next_step": patient_next_step(flag.status) if patient_view else None,
        "gap_answer": flag.gap_answer,
        "gap_detail": flag.gap_detail,
        "resolution_note": flag.resolution_note if (show or patient_view) and flag.status == "resolved" else None,
        "diagnosis_1": diagnosis_public(
            flag.diagnosis_1,
            include_notes=show,
            include_label=show_labels,
        ),
        "diagnosis_2": diagnosis_public(
            flag.diagnosis_2,
            include_notes=show,
            include_label=show_labels,
        ),
        "pending_review": flag.status != "resolved" and viewer_role != "doctor",
        "resolution_deadline": None if patient_view else (flag.resolution_deadline.isoformat() if flag.resolution_deadline else None),
        "assigned_doctor_id": flag.assigned_doctor_id,
        "assigned_doctor": doctor_public(flag.assigned_doctor) if flag.assigned_doctor and not patient_view else None,
        "judge_pool_open": bool(flag.judge_pool_open),
        "escalated": flag.status == "escalated",
        "guest_judge": None if patient_view else _active_guest_summary(flag),
    }
    return payload


def _active_guest_summary(flag: Flag) -> dict | None:
    invites = getattr(flag, "guest_invites", None) or []
    active = next((row for row in invites if row.status in {"invited", "accessed"}), None)
    done = next((row for row in invites if row.status == "judged"), None)
    row = active or done
    if not row:
        return None
    return {
        "status": row.status,
        "invited_name": row.invited_name,
        "invited_specialty": row.invited_specialty,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
    }


def _without_email(doctor_payload: dict | None) -> dict | None:
    if not doctor_payload:
        return None
    data = dict(doctor_payload)
    data.pop("email", None)
    return data


def guest_invite_public(invite: GuestJudgeInvite, *, include_token: bool = False) -> dict:
    inviter = invite.invited_by
    payload = {
        "id": invite.id,
        "flag_id": invite.flag_id,
        "invited_name": invite.invited_name,
        "invited_email": invite.invited_email,
        "invited_specialty": invite.invited_specialty,
        "status": invite.status,
        "verified": bool(invite.verified),
        "judgment_choice": invite.judgment_choice,
        "created_at": invite.created_at.isoformat() if invite.created_at else None,
        "expires_at": invite.expires_at.isoformat() if invite.expires_at else None,
        "invited_by_id": invite.invited_by_id,
        "invited_by": {
            "id": inviter.id,
            "name": inviter.name,
            "role": inviter.role,
        }
        if inviter
        else None,
        "access_path": f"/guest-judge/{invite.invite_token}",
    }
    if include_token:
        payload["invite_token"] = invite.invite_token
    return payload


def guest_invite_prefill(invite: GuestJudgeInvite) -> dict:
    return {
        "invite_token": invite.invite_token,
        "name": invite.invited_name,
        "email": invite.invited_email,
        "specialty": invite.invited_specialty,
        "license_number": invite.license_number,
        "verified": bool(invite.verified),
        "status": invite.status,
        "resolved_cases_count": 1 if invite.status == "judged" else 0,
    }


def guest_flag_packet(flag: Flag) -> dict:
    payload = flag_public(flag, viewer_role="doctor", reveal_detail=True)
    for key in ("diagnosis_1", "diagnosis_2"):
        dx = payload.get(key) or {}
        dx["doctor"] = _without_email(dx.get("doctor"))
        payload[key] = dx
    payload["assigned_doctor"] = _without_email(payload.get("assigned_doctor"))
    payload["patient_email"] = None
    return payload


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


def medical_report_public(report: MedicalReport) -> dict:
    doctor = report.doctor
    submitter = report.submitted_by if getattr(report, "submitted_by", None) else None
    return {
        "id": report.id,
        "patient_id": report.patient_id,
        "doctor_id": report.doctor_id,
        "doctor": doctor_public(doctor) if doctor else None,
        "related_issue": report.related_issue,
        "notes": report.notes or "",
        "source": report.source or "typed",
        "original_filename": report.original_filename,
        "file_url": f"/api/reports/{report.id}/file" if report.file_path else None,
        "has_image": bool(report.file_path and Path(report.original_filename or report.file_path).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif"}),
        "submitted_by": submitter.name if submitter else None,
        "report_date": report.report_date.isoformat() if report.report_date else None,
        "uploaded_at": report.uploaded_at.isoformat() if report.uploaded_at else None,
    }


def conversation_note_public(note: ConversationNote) -> dict:
    return {
        "id": note.id,
        "doctor": doctor_public(note.doctor) if note.doctor else None,
        "body": note.body,
        "created_at": note.created_at.isoformat() if note.created_at else None,
    }


def conversation_public(conversation: DoctorConversation, *, viewer_role: str) -> dict:
    patient_view = viewer_role in {"patient", "surrogate"}
    payload = {
        "id": conversation.id,
        "patient_id": conversation.patient_id,
        "patient_name": conversation.patient.user.name if conversation.patient and conversation.patient.user else None,
        "issue_type": conversation.issue_type,
        "status": conversation.status,
        "scheduled_time": conversation.scheduled_time.isoformat() if conversation.scheduled_time else None,
        "schedule_deadline": conversation.schedule_deadline.isoformat() if conversation.schedule_deadline else None,
        "duration_minutes": conversation.duration_minutes,
        "patient_status": conversation_patient_status(conversation),
        "patient_conclusion": conversation.patient_conclusion if conversation.status == "completed" else None,
        "senior_doctor": doctor_public(conversation.senior_doctor) if conversation.senior_doctor else None,
        "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
    }
    if patient_view:
        return payload
    submitted = {row.doctor_id for row in (conversation.availabilities or [])}
    payload.update(
        {
            "doctor_1": doctor_public(conversation.doctor_1) if conversation.doctor_1 else None,
            "doctor_2": doctor_public(conversation.doctor_2) if conversation.doctor_2 else None,
            "report_1": medical_report_public(conversation.report_1) if conversation.report_1 else None,
            "report_2": medical_report_public(conversation.report_2) if conversation.report_2 else None,
            "agreed": conversation.agreed,
            "conclusion": conversation.conclusion,
            "transcript_or_notes": conversation.transcript_or_notes,
            "notes": [conversation_note_public(note) for note in sorted(conversation.notes, key=lambda row: row.id)],
            "availability_submitted": sorted(submitted),
        }
    )
    return payload


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
