from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.age import is_minor
from app.catalog import DIAGNOSIS_LABELS, DISCLOSURE_REASONS
from app.database import get_db
from app.deps import (
    can_view_patient,
    doctor_access_status,
    get_current_user,
    get_doctor,
    get_patient_for_user,
    load_patient,
    require_doctor_access,
    require_write_for_patient,
)
from app.explainer import explain_process
from app.medrea import reply_to as medrea_reply
from app.flagging import evaluate_new_diagnosis, notify, notify_diagnosis_logged, notify_flag_resolved
from app.models import (
    AccessRequest,
    CorrectionSuggestion,
    Diagnosis,
    Flag,
    Notification,
    Patient,
    Surrogate,
    User,
)
from app.schemas import (
    AccessCreateRequest,
    CorrectionCreateRequest,
    DiagnosisCreateRequest,
    LoginRequest,
    MedreaChatRequest,
    ResolveFlagRequest,
)
from app.security import verify_password
from app.serialize import (
    access_public,
    correction_public,
    diagnosis_public,
    flag_public,
    me_payload,
    notification_public,
    patient_record,
)

router = APIRouter()


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    surrogate = db.query(Surrogate).filter(Surrogate.user_id == user.id).first()
    patient = None
    if user.role == "patient":
        patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    return me_payload(user, patient, surrogate)


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    surrogate = db.query(Surrogate).filter(Surrogate.user_id == user.id).first()
    patient = None
    if user.role == "patient":
        patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    return me_payload(user, patient, surrogate)


@router.get("/explainer")
def explainer(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    patient = get_patient_for_user(user, db)
    if not patient:
        raise HTTPException(status_code=400, detail="Explainer is for patients and surrogates")
    viewer_is_minor = user.role == "patient" and is_minor(user.date_of_birth)
    open_flags = db.query(Flag).filter(Flag.patient_id == patient.id, Flag.status != "resolved").count()
    resolved_flags = db.query(Flag).filter(Flag.patient_id == patient.id, Flag.status == "resolved").count()
    disclosed_rows = (
        db.query(Diagnosis)
        .filter(Diagnosis.patient_id == patient.id, Diagnosis.disclose_to_patient.is_(True))
        .order_by(Diagnosis.id.asc())
        .all()
    )
    payload = explain_process(
        viewer_is_minor=viewer_is_minor,
        patient_name=patient.user.name,
        open_flag_count=open_flags,
        resolved_flag_count=resolved_flags,
        disclosed_diagnosis_count=len(disclosed_rows),
    )
    payload["original_notes"] = [
        {
            "label": dx.diagnosis_label,
            "full_notes": dx.full_notes,
            "doctor": dx.doctor.user.name,
            "timestamp": dx.timestamp.isoformat() if dx.timestamp else None,
        }
        for dx in disclosed_rows
    ]
    return payload


@router.post("/medrea/chat")
def medrea_chat(body: MedreaChatRequest):
    return {"reply": medrea_reply(body.messages, body.report)}


@router.get("/catalog/diagnoses")
def diagnosis_catalog():
    return {"labels": DIAGNOSIS_LABELS, "disclosure_reasons": DISCLOSURE_REASONS}


@router.get("/patients")
def list_patients(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role == "doctor":
        doctor = get_doctor(user, db)
        rows = db.query(Patient).all()
        out = []
        for p in rows:
            status_value = doctor_access_status(db, doctor.id, p.id)
            record = patient_record(p, status_value)
            if status_value != "approved":
                record["conditions"] = []
                record["medications"] = []
            out.append(record)
        return out
    patient = get_patient_for_user(user, db)
    if not patient:
        return []
    return [patient_record(patient)]


@router.get("/patients/{patient_id}")
def get_patient(patient_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    patient = load_patient(db, patient_id)
    if user.role == "doctor":
        doctor = get_doctor(user, db)
        status_value = doctor_access_status(db, doctor.id, patient.id)
        record = patient_record(patient, status_value)
        if status_value != "approved":
            record["conditions"] = []
            record["medications"] = []
        return record
    if not can_view_patient(db, user, patient):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot view this record")
    return patient_record(patient)


@router.post("/access-requests")
def request_access(
    body: AccessCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors request access")
    doctor = get_doctor(user, db)
    patient = load_patient(db, body.patient_id)
    existing = doctor_access_status(db, doctor.id, patient.id)
    if existing == "approved":
        raise HTTPException(status_code=400, detail="Access already approved")
    if existing == "pending":
        raise HTTPException(status_code=400, detail="Access request already pending")
    req = AccessRequest(doctor_id=doctor.id, patient_id=patient.id, status="pending")
    db.add(req)
    db.flush()
    msg = f"{user.name} requested access to {patient.user.name}'s record."
    if is_minor(patient.user.date_of_birth) and patient.surrogate:
        notify(db, patient.surrogate.user_id, "access_requested", msg, req.id)
    else:
        notify(db, patient.user_id, "access_requested", msg, req.id)
    db.commit()
    db.refresh(req)
    return access_public(req)


@router.get("/access-requests")
def list_access(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role == "doctor":
        doctor = get_doctor(user, db)
        rows = db.query(AccessRequest).filter(AccessRequest.doctor_id == doctor.id).all()
        return [access_public(r) for r in rows]
    patient = get_patient_for_user(user, db)
    if not patient:
        return []
    rows = db.query(AccessRequest).filter(AccessRequest.patient_id == patient.id).all()
    return [access_public(r) for r in rows]


def _set_access_status(db: Session, user: User, request_id: int, new_status: str):
    req = db.get(AccessRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Access request not found")
    require_write_for_patient(db, user, req.patient)
    if req.status != "pending":
        raise HTTPException(status_code=400, detail="Request is no longer pending")
    req.status = new_status
    verb = "approved" if new_status == "approved" else "denied"
    notify(
        db,
        req.doctor.user_id,
        f"access_{verb}",
        f"Access to {req.patient.user.name} was {verb}.",
        req.id,
    )
    db.commit()
    db.refresh(req)
    return access_public(req)


@router.post("/access-requests/{request_id}/approve")
def approve_access(request_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _set_access_status(db, user, request_id, "approved")


@router.post("/access-requests/{request_id}/deny")
def deny_access(request_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _set_access_status(db, user, request_id, "denied")


@router.post("/diagnoses")
def create_diagnosis(
    body: DiagnosisCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors log diagnoses")
    if body.diagnosis_label not in DIAGNOSIS_LABELS:
        raise HTTPException(status_code=400, detail="Choose a structured diagnosis label")
    doctor = get_doctor(user, db)
    patient = load_patient(db, body.patient_id)
    require_doctor_access(db, doctor, patient)
    if not body.disclose_to_patient:
        reason = (body.disclosure_reason or "").strip()
        if reason not in DISCLOSURE_REASONS:
            raise HTTPException(status_code=400, detail="Choose a disclosure reason")
    else:
        reason = None
    dx = Diagnosis(
        patient_id=patient.id,
        doctor_id=doctor.id,
        diagnosis_label=body.diagnosis_label,
        full_notes=body.full_notes.strip(),
        disclose_to_patient=body.disclose_to_patient,
        disclosure_reason=reason,
    )
    db.add(dx)
    db.flush()
    notify_diagnosis_logged(db, dx)
    flags = evaluate_new_diagnosis(db, dx)
    db.commit()
    db.refresh(dx)
    return {
        "diagnosis": diagnosis_public(dx, include_notes=True, include_label=True),
        "flags_raised": [flag_public(f, viewer_role="doctor", reveal_detail=True) for f in flags],
    }


@router.get("/diagnoses")
def list_diagnoses(
    patient_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    patient = load_patient(db, patient_id)
    rows = db.query(Diagnosis).filter(Diagnosis.patient_id == patient.id).order_by(Diagnosis.id.asc()).all()
    if user.role == "doctor":
        doctor = get_doctor(user, db)
        require_doctor_access(db, doctor, patient)
        return [diagnosis_public(dx, include_notes=True, include_label=True) for dx in rows]
    if not can_view_patient(db, user, patient):
        raise HTTPException(status_code=403, detail="Cannot view diagnoses")
    visible = []
    is_surrogate = user.role == "surrogate"
    for dx in rows:
        if dx.disclose_to_patient:
            visible.append(diagnosis_public(dx, include_notes=True, include_label=True))
        elif is_surrogate:
            visible.append(diagnosis_public(dx, include_notes=True, include_label=True))
    return visible


@router.get("/flags")
def list_flags(
    patient_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Flag)
    if user.role == "doctor":
        doctor = get_doctor(user, db)
        flags = query.order_by(Flag.id.desc()).all()
        result = []
        for flag in flags:
            if doctor_access_status(db, doctor.id, flag.patient_id) != "approved":
                continue
            if patient_id and flag.patient_id != patient_id:
                continue
            involved = {flag.diagnosis_1.doctor_id, flag.diagnosis_2.doctor_id}
            if doctor.id not in involved:
                # still show if they have access — helpful for the other attending doctor
                pass
            result.append(flag_public(flag, viewer_role="doctor", reveal_detail=True))
        return result
    patient = get_patient_for_user(user, db)
    if not patient:
        return []
    flags = query.filter(Flag.patient_id == patient.id).order_by(Flag.id.desc()).all()
    out = []
    for flag in flags:
        reveal = flag.status == "resolved"
        out.append(flag_public(flag, viewer_role=user.role, reveal_detail=reveal))
    return out


@router.post("/flags/{flag_id}/review")
def review_flag(flag_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors review flags")
    flag = db.get(Flag, flag_id)
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    doctor = get_doctor(user, db)
    require_doctor_access(db, doctor, flag.patient)
    if flag.status == "open":
        flag.status = "under_review"
        db.commit()
        db.refresh(flag)
    return flag_public(flag, viewer_role="doctor", reveal_detail=True)


@router.post("/flags/{flag_id}/resolve")
def resolve_flag(
    flag_id: int,
    body: ResolveFlagRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors resolve flags")
    flag = db.get(Flag, flag_id)
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    doctor = get_doctor(user, db)
    require_doctor_access(db, doctor, flag.patient)
    involved = {flag.diagnosis_1.doctor_id, flag.diagnosis_2.doctor_id}
    if doctor.id not in involved:
        raise HTTPException(status_code=403, detail="Only the doctors on this flag can resolve it")
    if flag.status == "resolved":
        raise HTTPException(status_code=400, detail="Flag already resolved")
    flag.status = "resolved"
    flag.resolution_note = body.resolution_note.strip()
    notify_flag_resolved(db, flag)
    db.commit()
    db.refresh(flag)
    return flag_public(flag, viewer_role="doctor", reveal_detail=True)


@router.get("/notifications")
def list_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Notification)
        .filter(Notification.user_id == user.id)
        .order_by(Notification.id.desc())
        .all()
    )
    return [notification_public(n) for n in rows]


@router.post("/notifications/{note_id}/read")
def mark_read(note_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    note = db.get(Notification, note_id)
    if not note or note.user_id != user.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    note.read = True
    db.commit()
    return notification_public(note)


@router.get("/corrections")
def list_corrections(
    patient_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    patient = load_patient(db, patient_id)
    if user.role == "doctor":
        doctor = get_doctor(user, db)
        require_doctor_access(db, doctor, patient)
    elif not can_view_patient(db, user, patient):
        raise HTTPException(status_code=403, detail="Cannot view corrections")
    rows = (
        db.query(CorrectionSuggestion)
        .filter(CorrectionSuggestion.patient_id == patient.id)
        .order_by(CorrectionSuggestion.id.desc())
        .all()
    )
    return [correction_public(c) for c in rows]


@router.post("/corrections")
def create_correction(
    body: CorrectionCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    patient = load_patient(db, body.patient_id)
    require_write_for_patient(db, user, patient)
    if body.field not in ("conditions", "medications"):
        raise HTTPException(status_code=400, detail="Field must be conditions or medications")
    item = CorrectionSuggestion(
        patient_id=patient.id,
        submitted_by_user_id=user.id,
        field=body.field,
        proposed_value=body.proposed_value.strip(),
        status="pending",
    )
    db.add(item)
    db.flush()
    if user.role == "doctor":
        pass
    db.commit()
    db.refresh(item)
    return correction_public(item)
