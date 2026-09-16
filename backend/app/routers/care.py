from __future__ import annotations

import mimetypes
from datetime import date, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import (
    doctor_access_status,
    get_current_user,
    get_doctor,
    get_patient_for_user,
    load_patient,
    require_doctor_access,
    require_write_for_patient,
)
from app.flagging import notify
from app.models import AccessRequest, ConversationNote, Diagnosis, Doctor, DoctorConversation, Flag, MedicalReport, User
from app.schemas import AvailabilityRequest, ConversationCompleteRequest, ConversationNoteRequest, GapResponseRequest
from app.serialize import conversation_public, doctor_public, flag_public, medical_report_public
from logic.report_conflict import (
    check_duplicate_issue_reports,
    complete_conversation,
    enforce_schedule_deadlines,
    upsert_availability,
)
from app.storage import is_image_name, resolve_report_file, save_report_file
from logic.report_ingest import MAX_UPLOAD_BYTES, clip_notes, ingest_report_file

router = APIRouter()


def _patient_from_request(user: User, db: Session, patient_id: int | str | None, *, require_treatment_access: bool = True) -> object:
    parsed = None
    if patient_id not in (None, "", "null", "undefined"):
        try:
            parsed = int(patient_id)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="Invalid patient_id") from exc
    if user.role in {"patient", "surrogate"}:
        patient = get_patient_for_user(user, db)
        if not patient:
            raise HTTPException(status_code=400, detail="No patient record for this account")
        if parsed and patient.id != parsed:
            raise HTTPException(status_code=403, detail="Cannot upload for another patient")
        return patient
    if user.role != "doctor":
        raise HTTPException(status_code=403, detail="Not allowed")
    if not parsed:
        raise HTTPException(status_code=400, detail="patient_id is required")
    patient = load_patient(db, parsed)
    if require_treatment_access:
        require_doctor_access(db, get_doctor(user, db), patient)
    return patient


def _conversation_for_doctor(db: Session, conversation_id: int, doctor_id: int) -> DoctorConversation:
    conversation = db.get(DoctorConversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    allowed = {conversation.doctor_id_1, conversation.doctor_id_2, conversation.senior_doctor_id}
    if doctor_id not in allowed:
        raise HTTPException(status_code=403, detail="You are not part of this conversation")
    return conversation


@router.get("/care-circle")
def care_circle(
    patient_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role in {"patient", "surrogate"}:
        patient = get_patient_for_user(user, db)
        if not patient:
            return []
    elif user.role == "doctor":
        if not patient_id:
            return []
        patient = load_patient(db, patient_id)
        require_doctor_access(db, get_doctor(user, db), patient)
    else:
        return []
    rows = (
        db.query(AccessRequest)
        .filter(AccessRequest.patient_id == patient.id, AccessRequest.status == "approved")
        .all()
    )
    doctors = [doctor_public(row.doctor) for row in rows]
    doctors.sort(key=lambda item: item.get("credibility_score") or 0, reverse=True)
    return doctors


@router.get("/timeline")
def patient_timeline(
    patient_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    patient = _patient_from_request(user, db, patient_id, require_treatment_access=False)
    items = []
    diagnoses = db.query(Diagnosis).filter(Diagnosis.patient_id == patient.id).all()
    is_surrogate = user.role == "surrogate"
    doctor = get_doctor(user, db) if user.role == "doctor" else None
    treatment_ok = user.role != "doctor" or doctor_access_status(db, doctor.id, patient.id) == "approved"
    if treatment_ok:
        for dx in diagnoses:
            if user.role == "patient" and not dx.disclose_to_patient:
                continue
            if user.role == "doctor" or is_surrogate or dx.disclose_to_patient:
                notes = (dx.full_notes or "").strip()
                items.append(
                    {
                        "id": f"dx-{dx.id}",
                        "type": "diagnosis",
                        "kind": "Diagnosis",
                        "date": dx.timestamp.isoformat() if dx.timestamp else None,
                        "doctor_name": dx.doctor.user.name if dx.doctor and dx.doctor.user else None,
                        "title": dx.diagnosis_label,
                        "summary": notes[:220] if notes else dx.diagnosis_label,
                        "report_id": None,
                    }
                )
        for med in patient.medications or []:
            label = str(med).strip()
            if not label:
                continue
            items.append(
                {
                    "id": f"rx-{label}",
                    "type": "prescription",
                    "kind": "Prescription",
                    "date": None,
                    "doctor_name": None,
                    "title": label,
                    "summary": "On file in your medication list",
                    "report_id": None,
                }
            )
    reports = db.query(MedicalReport).filter(MedicalReport.patient_id == patient.id).all()
    for report in reports:
        if user.role == "doctor" and not treatment_ok and report.doctor_id != doctor.id:
            continue
        doctor_name = report.doctor.user.name if report.doctor and report.doctor.user else "Uploaded by you"
        items.append(
            {
                "id": f"report-{report.id}",
                "type": "report",
                "kind": "Medical report",
                "date": (report.report_date.isoformat() if report.report_date else None)
                or (report.uploaded_at.isoformat() if report.uploaded_at else None),
                "doctor_name": doctor_name,
                "title": report.related_issue,
                "summary": (report.notes or "").strip()[:220] or report.related_issue,
                "report_id": report.id,
                "file_url": f"/api/reports/{report.id}/file" if report.file_path else None,
                "has_image": bool(report.file_path and is_image_name(report.original_filename or report.file_path)),
                "original_filename": report.original_filename,
            }
        )
    items.sort(key=lambda row: row.get("date") or "", reverse=True)
    return items


@router.get("/reports")
def list_reports(
    patient_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    patient = _patient_from_request(user, db, patient_id, require_treatment_access=False)
    query = db.query(MedicalReport).filter(MedicalReport.patient_id == patient.id)
    if user.role == "doctor":
        doctor = get_doctor(user, db)
        if doctor_access_status(db, doctor.id, patient.id) != "approved":
            query = query.filter(MedicalReport.doctor_id == doctor.id)
    rows = query.order_by(MedicalReport.uploaded_at.desc()).all()
    return [medical_report_public(row) for row in rows]


async def _read_optional_upload(file: UploadFile | None) -> tuple[bytes | None, str | None]:
    if file is None:
        return None, None
    filename = (file.filename or "").strip() or None
    payload = await file.read()
    if payload and len(payload) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File exceeds the 12 MB limit")
    return (payload or None), filename


@router.post("/reports")
async def upload_report(
    related_issue: str | None = Form(None),
    notes: str | None = Form(None),
    source: str | None = Form(None),
    file: UploadFile | None = File(None),
    report_date: str | None = Form(None),
    doctor_id: str | None = Form(None),
    patient_id: str | None = Form(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role in {"patient", "surrogate"}:
        patient = _patient_from_request(user, db, patient_id, require_treatment_access=False)
        require_write_for_patient(db, user, patient)
    elif user.role == "doctor":
        patient = _patient_from_request(user, db, patient_id, require_treatment_access=False)
    else:
        raise HTTPException(status_code=403, detail="Not allowed")
    typed = clip_notes(notes or "")
    payload, filename = await _read_optional_upload(file)
    extracted = ""
    if payload is not None:
        try:
            extracted = ingest_report_file(payload, filename or "upload")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    combined = "\n\n".join(part for part in (typed, extracted) if part).strip()
    issue = (related_issue or "").strip()
    if not issue:
        issue = ((typed.splitlines()[0] if typed else "") or (filename or "Report"))[:160]
    if not typed and payload is None:
        raise HTTPException(status_code=400, detail="Type the report, upload a file, or scan a page")
    if not combined:
        combined = issue
    kind = (source or "").strip().lower()
    if kind not in {"typed", "upload", "scan"}:
        kind = "upload" if filename else "typed"
    parsed_date = None
    if report_date:
        try:
            parsed_date = date.fromisoformat(report_date)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="report_date must be YYYY-MM-DD") from exc
    linked_doctor_id = None
    if doctor_id not in (None, "", "null", "undefined"):
        try:
            linked_doctor_id = int(doctor_id)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="Invalid doctor_id") from exc
        linked = db.get(Doctor, linked_doctor_id)
        if not linked:
            raise HTTPException(status_code=400, detail="Doctor not found")
    if user.role == "doctor" and not linked_doctor_id:
        linked_doctor_id = get_doctor(user, db).id

    report = MedicalReport(
        patient_id=patient.id,
        doctor_id=linked_doctor_id,
        submitted_by_user_id=user.id,
        related_issue=issue[:160],
        notes=combined,
        source=kind,
        original_filename=filename,
        report_date=parsed_date,
    )
    db.add(report)
    db.flush()
    if payload and filename:
        report.file_path = save_report_file(report.id, filename, payload)
        report.notes = (
            (report.notes or "")
            .replace(" Original file was not saved.", "")
            .replace("Original file was not saved.", "")
            .strip()
            or issue
        )
    if linked_doctor_id and user.role in {"patient", "surrogate"}:
        linked = db.get(Doctor, linked_doctor_id)
        if linked:
            notify(
                db,
                linked.user_id,
                "report_shared",
                f"{patient.user.name} sent you a report ({issue}). Previous treatment still needs a request.",
                report.id,
            )
    if user.role == "doctor":
        notify(
            db,
            patient.user_id,
            "report_shared",
            f"{user.name} added a report ({issue}).",
            report.id,
        )
    conversation = check_duplicate_issue_reports(db, patient.id, report)
    db.commit()
    db.refresh(report)
    payload = medical_report_public(report)
    payload["conversation"] = (
        conversation_public(conversation, viewer_role=user.role) if conversation else None
    )
    return payload


def _can_see_report(user: User, db: Session, report: MedicalReport) -> bool:
    if user.role in {"patient", "surrogate"}:
        patient = get_patient_for_user(user, db)
        return bool(patient and patient.id == report.patient_id)
    if user.role != "doctor":
        return False
    doctor = get_doctor(user, db)
    if report.doctor_id == doctor.id:
        return True
    if doctor_access_status(db, doctor.id, report.patient_id) == "approved":
        return True
    linked = (
        db.query(DoctorConversation)
        .filter(
            or_(
                DoctorConversation.report_id_1 == report.id,
                DoctorConversation.report_id_2 == report.id,
            ),
            or_(
                DoctorConversation.doctor_id_1 == doctor.id,
                DoctorConversation.doctor_id_2 == doctor.id,
                DoctorConversation.senior_doctor_id == doctor.id,
            ),
        )
        .first()
    )
    return bool(linked)


@router.get("/reports/{report_id}/file")
def download_report_file(
    report_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = db.get(MedicalReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if not _can_see_report(user, db, report):
        raise HTTPException(status_code=403, detail="Not allowed")
    path = resolve_report_file(report.file_path)
    if not path:
        raise HTTPException(status_code=404, detail="File is not available")
    media = mimetypes.guess_type(report.original_filename or path.name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media, filename=report.original_filename or path.name)


@router.post("/flags/{flag_id}/gap-response")
def gap_response(
    flag_id: int,
    body: GapResponseRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    flag = db.get(Flag, flag_id)
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    patient = get_patient_for_user(user, db)
    if not patient or patient.id != flag.patient_id:
        raise HTTPException(status_code=403, detail="Only this patient or surrogate can respond")
    require_write_for_patient(db, user, patient)
    answer = body.answer.strip().lower()
    if answer not in {"yes", "no", "detail"}:
        raise HTTPException(status_code=400, detail="Answer must be yes, no, or detail")
    flag.gap_answer = answer
    flag.gap_detail = body.detail.strip() if answer == "detail" else ""
    d1 = flag.diagnosis_1
    d2 = flag.diagnosis_2
    msg = f"{user.name} responded to a disclosure question on a review for {patient.user.name}: {answer}"
    if flag.gap_detail:
        msg += f" — {flag.gap_detail}"
    notify(db, d1.doctor.user_id, "gap_response", msg, flag.id)
    notify(db, d2.doctor.user_id, "gap_response", msg, flag.id)
    db.commit()
    db.refresh(flag)
    return flag_public(flag, viewer_role=user.role, reveal_detail=flag.status == "resolved")


@router.get("/conversations")
def list_conversations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    enforce_schedule_deadlines(db)
    db.commit()
    if user.role == "doctor":
        doctor = get_doctor(user, db)
        rows = (
            db.query(DoctorConversation)
            .filter(
                (DoctorConversation.doctor_id_1 == doctor.id)
                | (DoctorConversation.doctor_id_2 == doctor.id)
                | (DoctorConversation.senior_doctor_id == doctor.id)
            )
            .order_by(DoctorConversation.id.desc())
            .all()
        )
        return [conversation_public(row, viewer_role="doctor") for row in rows]
    patient = get_patient_for_user(user, db)
    if not patient:
        return []
    rows = (
        db.query(DoctorConversation)
        .filter(DoctorConversation.patient_id == patient.id)
        .order_by(DoctorConversation.id.desc())
        .all()
    )
    return [conversation_public(row, viewer_role=user.role) for row in rows]


@router.get("/conversations/{conversation_id}")
def get_conversation(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = db.get(DoctorConversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if user.role == "doctor":
        _conversation_for_doctor(db, conversation_id, get_doctor(user, db).id)
        return conversation_public(conversation, viewer_role="doctor")
    patient = get_patient_for_user(user, db)
    if not patient or patient.id != conversation.patient_id:
        raise HTTPException(status_code=403, detail="Cannot view this conversation")
    return conversation_public(conversation, viewer_role=user.role)


@router.post("/conversations/{conversation_id}/availability")
def submit_availability(
    conversation_id: int,
    body: AvailabilityRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors submit availability")
    doctor = get_doctor(user, db)
    conversation = _conversation_for_doctor(db, conversation_id, doctor.id)
    if conversation.senior_doctor_id == doctor.id:
        raise HTTPException(status_code=400, detail="The reviewing specialist does not need to pick a slot")
    upsert_availability(db, conversation, doctor, body.slots)
    db.commit()
    db.refresh(conversation)
    return conversation_public(conversation, viewer_role="doctor")


@router.post("/conversations/{conversation_id}/notes")
def add_conversation_note(
    conversation_id: int,
    body: ConversationNoteRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors add notes")
    doctor = get_doctor(user, db)
    conversation = _conversation_for_doctor(db, conversation_id, doctor.id)
    text = body.body.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Note cannot be empty")
    db.add(ConversationNote(conversation_id=conversation.id, doctor_id=doctor.id, body=text))
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    existing = conversation.transcript_or_notes or ""
    line = f"[{stamp}] {doctor.user.name}: {text}"
    conversation.transcript_or_notes = f"{existing}\n{line}".strip() if existing else line
    if conversation.status == "scheduled":
        conversation.status = "in_progress"
    db.commit()
    db.refresh(conversation)
    return conversation_public(conversation, viewer_role="doctor")


@router.post("/conversations/{conversation_id}/complete")
def mark_conversation_complete(
    conversation_id: int,
    body: ConversationCompleteRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors complete conversations")
    doctor = get_doctor(user, db)
    conversation = _conversation_for_doctor(db, conversation_id, doctor.id)
    if conversation.status == "completed":
        raise HTTPException(status_code=400, detail="Conversation already completed")
    is_senior = conversation.senior_doctor_id == doctor.id
    if conversation.senior_doctor_id and not is_senior:
        raise HTTPException(status_code=400, detail="Waiting on the reviewing specialist")
    complete_conversation(
        db,
        conversation,
        conclusion=body.conclusion,
        agreed=body.agreed,
        acting_doctor=doctor,
        good_treatment=body.good_treatment,
    )
    db.commit()
    db.refresh(conversation)
    return conversation_public(conversation, viewer_role="doctor")
