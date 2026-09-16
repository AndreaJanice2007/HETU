from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.accounts import create_user_account, ensure_usernames, find_user_by_identifier
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
from logic.escalation import (
    accept_flag_to_judge,
    check_expired_flags,
    credit_resolver_if_reviewing,
    decline_judge,
    matching_third_doctors,
)
from logic.guest_judge import (
    access_guest_invite,
    complete_doctor_signup_from_invite,
    create_guest_invite,
    expire_guest_invites,
    internal_pool_status,
    load_guest_invite,
    mark_guest_accessed,
    submit_guest_judgment,
)
from app.models import (
    AccessRequest,
    CorrectionSuggestion,
    Diagnosis,
    Doctor,
    Flag,
    GuestJudgeInvite,
    MedicalReport,
    Notification,
    Patient,
    Surrogate,
    User,
)
from app.schemas import (
    AccessCreateRequest,
    CorrectionCreateRequest,
    DiagnosisCreateRequest,
    DoctorSignupRequest,
    GuestJudgeInviteRequest,
    GuestJudgmentRequest,
    GuestLicenseRequest,
    LoginRequest,
    MedreaChatRequest,
    ResolveFlagRequest,
    SignupRequest,
)
from app.security import verify_password
from app.serialize import (
    access_public,
    correction_public,
    diagnosis_public,
    doctor_public,
    flag_public,
    guest_flag_packet,
    guest_invite_prefill,
    guest_invite_public,
    me_payload,
    notification_public,
    patient_record,
)

router = APIRouter()


def _run_escalation_checks(db: Session) -> None:
    expired_flags = check_expired_flags(db)
    expired_invites = expire_guest_invites(db)
    if expired_flags or expired_invites:
        db.commit()


def _guest_case_payload(invite) -> dict:
    payload = guest_invite_public(invite, include_token=False)
    payload["license_verified"] = bool(invite.verified)
    payload["flag"] = guest_flag_packet(invite.flag)
    payload["disclaimer"] = (
        "Hetu does not diagnose. This guest review is a suggestion for the "
        "attending doctors, not a verdict."
    )
    return payload


def _create_external_invite(flag_id, body, user, db):
    if user.role not in {"doctor", "admin"}:
        raise HTTPException(
            status_code=403,
            detail="Only a registered doctor or admin can invite an external guest judge",
        )
    _run_escalation_checks(db)
    flag = db.get(Flag, flag_id)
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    if user.role == "doctor":
        get_doctor(user, db)
    try:
        invite = create_guest_invite(
            db,
            flag,
            user,
            invited_name=body.invited_name,
            invited_email=body.invited_email,
            invited_specialty=body.invited_specialty,
            license_number=body.license_number,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    notify(
        db,
        user.id,
        "guest_judge_invite",
        (
            f"Guest review invite created for {invite.invited_name}. "
            f"Share the access link. Demo does not send email."
        ),
        flag.id,
    )
    db.commit()
    db.refresh(invite)
    payload = guest_invite_public(invite, include_token=True)
    payload["pool"] = internal_pool_status(db, flag)
    return payload


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    ident = (body.identifier or body.username or body.email or "").strip()
    user = find_user_by_identifier(db, ident)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This email or username has not signed up yet. Create an account first.",
        )
    if not verify_password(body.password, user.password_hash):
        if user.role == "surrogate":
            surrogate_row = db.query(Surrogate).filter(Surrogate.user_id == user.id).first()
            linked = db.get(Patient, surrogate_row.linked_patient_id) if surrogate_row else None
            if not linked or not linked.user or not verify_password(body.password, linked.user.password_hash):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password")
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password")
    surrogate = db.query(Surrogate).filter(Surrogate.user_id == user.id).first()
    patient = None
    if user.role == "patient":
        patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    return me_payload(user, patient, surrogate)


@router.post("/signup")
def signup(body: SignupRequest, db: Session = Depends(get_db)):
    role = (body.role or "").strip().lower()
    if role not in {"patient", "doctor", "surrogate"}:
        raise HTTPException(status_code=400, detail="Choose patient, doctor, or surrogate")
    if body.password != body.confirm_password:
        raise HTTPException(status_code=400, detail="Password and confirmation do not match")
    try:
        user = create_user_account(
            db,
            name=body.name,
            email=body.email,
            password=body.password,
            role=role,
            linked_patient_email=body.linked_patient_email,
            age=body.age,
            specialty=body.specialty,
            hospital=body.hospital,
            years_experience=body.years_experience,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(user)
    surrogate = db.query(Surrogate).filter(Surrogate.user_id == user.id).first()
    patient = db.query(Patient).filter(Patient.user_id == user.id).first() if role == "patient" else None
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
    payload["original_notes"] = []
    return payload


@router.post("/medrea/chat")
def medrea_chat(body: MedreaChatRequest):
    return {"reply": medrea_reply(body.messages, body.report)}


@router.get("/catalog/diagnoses")
def diagnosis_catalog():
    return {"labels": DIAGNOSIS_LABELS, "disclosure_reasons": DISCLOSURE_REASONS}


@router.get("/patients/search")
def search_patients(
    q: str = "",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors search patients")
    doctor = get_doctor(user, db)
    term = (q or "").strip()
    if len(term) < 2:
        return []
    lowered = term.lower()
    out = []
    for patient in db.query(Patient).all():
        person = patient.user
        if not person:
            continue
        haystack = f"{person.name} {person.username or ''} {person.email}".lower()
        if lowered not in haystack:
            continue
        status_value = doctor_access_status(db, doctor.id, patient.id)
        record = patient_record(patient, status_value)
        if status_value != "approved":
            record["conditions"] = []
            record["medications"] = []
        out.append(record)
    out.sort(key=lambda row: (row.get("name") or "").lower())
    return out[:20]


@router.get("/doctors/rank")
def doctor_rank_board(db: Session = Depends(get_db)):
    rows = [row for row in db.query(Doctor).all() if row.user]
    rows.sort(
        key=lambda doctor: (
            doctor.credibility_score or 0,
            doctor.resolved_cases_count or 0,
            doctor.years_experience or 0,
            doctor.research_count or 0,
        ),
        reverse=True,
    )
    board = []
    for index, doctor in enumerate(rows, start=1):
        card = doctor_public(doctor)
        card["rank"] = index
        board.append(card)
    return board


@router.get("/doctors")
def list_doctors(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role not in {"patient", "surrogate", "doctor"}:
        raise HTTPException(status_code=403, detail="Not allowed")
    rows = db.query(Doctor).all()
    out = [doctor_public(row) for row in rows if row.user]
    out.sort(key=lambda row: (row.get("name") or "").lower())
    return out


@router.get("/patients")
def list_patients(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role == "doctor":
        doctor = get_doctor(user, db)
        by_id = {}
        linked = db.query(AccessRequest).filter(AccessRequest.doctor_id == doctor.id).all()
        for req in linked:
            record = patient_record(req.patient, req.status)
            if req.status != "approved":
                record["conditions"] = []
                record["medications"] = []
            by_id[req.patient_id] = record
        report_rows = db.query(MedicalReport).filter(MedicalReport.doctor_id == doctor.id).all()
        for report in report_rows:
            if report.patient_id in by_id:
                continue
            status_value = doctor_access_status(db, doctor.id, report.patient_id)
            record = patient_record(report.patient, status_value)
            record["conditions"] = []
            record["medications"] = []
            by_id[report.patient_id] = record
        return list(by_id.values())
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
    msg = f"{user.name} requested access to previous treatment for {patient.user.name}."
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
        f"Access to previous treatment for {req.patient.user.name} was {verb}.",
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
    _run_escalation_checks(db)
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
    _run_escalation_checks(db)
    query = db.query(Flag)
    if user.role == "doctor":
        doctor = get_doctor(user, db)
        flags = query.order_by(Flag.id.desc()).all()
        result = []
        for flag in flags:
            if doctor_access_status(db, doctor.id, flag.patient_id) != "approved":
                if flag.assigned_doctor_id != doctor.id:
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
    db.commit()
    return out


@router.post("/flags/{flag_id}/review")
def review_flag(flag_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors review flags")
    _run_escalation_checks(db)
    flag = db.get(Flag, flag_id)
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    doctor = get_doctor(user, db)
    if doctor.id != flag.assigned_doctor_id:
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
    _run_escalation_checks(db)
    flag = db.get(Flag, flag_id)
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    doctor = get_doctor(user, db)
    involved = {flag.diagnosis_1.doctor_id, flag.diagnosis_2.doctor_id}
    if doctor.id != flag.assigned_doctor_id:
        require_doctor_access(db, doctor, flag.patient)
    if doctor.id not in involved and doctor.id != flag.assigned_doctor_id:
        raise HTTPException(status_code=403, detail="Only the doctors on this flag can resolve it")
    if flag.status == "resolved":
        raise HTTPException(status_code=400, detail="Flag already resolved")
    flag.status = "resolved"
    flag.resolution_note = body.resolution_note.strip()
    credit_resolver_if_reviewing(flag, doctor)
    notify_flag_resolved(db, flag)
    db.commit()
    db.refresh(flag)
    return flag_public(flag, viewer_role="doctor", reveal_detail=True)


@router.get("/flags/{flag_id}/judge-pool")
def flag_judge_pool(flag_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can view the review pool")
    _run_escalation_checks(db)
    flag = db.get(Flag, flag_id)
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    doctor = get_doctor(user, db)
    declined_ids = {row.doctor_id for row in (flag.judge_declines or [])}
    pool = matching_third_doctors(db, flag)
    return {
        "flag_id": flag.id,
        "status": flag.status,
        "severity": flag.severity,
        "judge_pool_open": bool(flag.judge_pool_open),
        "assigned_doctor": doctor_public(flag.assigned_doctor) if flag.assigned_doctor else None,
        "you_declined": doctor.id in declined_ids,
        "declined_doctor_ids": sorted(declined_ids),
        "doctors": [doctor_public(item) for item in pool],
        **internal_pool_status(db, flag),
    }


@router.post("/flags/{flag_id}/accept-to-judge")
def accept_to_judge(flag_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can accept to judge")
    _run_escalation_checks(db)
    flag = db.get(Flag, flag_id)
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    doctor = get_doctor(user, db)
    if flag.assigned_doctor_id:
        raise HTTPException(status_code=409, detail="This flag already has a reviewing doctor")
    try:
        accept_flag_to_judge(db, flag, doctor)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    db.commit()
    db.refresh(flag)
    return flag_public(flag, viewer_role="doctor", reveal_detail=True)


@router.post("/flags/{flag_id}/decline-judge")
def decline_to_judge(flag_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Intentional by design: this endpoint logs the decline for analytics only.
    # It must never decrement credibility_score. Non-participation is not penalized.
    if user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can decline to judge")
    _run_escalation_checks(db)
    flag = db.get(Flag, flag_id)
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    doctor = get_doctor(user, db)
    try:
        record = decline_judge(db, flag_id, doctor.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(flag)
    return {
        "flag_id": flag.id,
        "doctor_id": doctor.id,
        "declined": True,
        "logged_at": record.timestamp.isoformat() if record.timestamp else None,
        "credibility_score": doctor.credibility_score,
        "credibility_unchanged": True,
        "assigned_doctor": doctor_public(flag.assigned_doctor) if flag.assigned_doctor else None,
        "judge_pool_open": bool(flag.judge_pool_open),
    }


@router.post("/flags/{flag_id}/invite-external-doctor")
def invite_external_doctor(
    flag_id: int,
    body: GuestJudgeInviteRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _create_external_invite(flag_id, body, user, db)


@router.post("/flags/{flag_id}/guest-judge-invites")
def create_flag_guest_invite(
    flag_id: int,
    body: GuestJudgeInviteRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _create_external_invite(flag_id, body, user, db)


@router.get("/flags/{flag_id}/guest-judge-invites")
def list_flag_guest_invites(
    flag_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can list guest invites")
    _run_escalation_checks(db)
    flag = db.get(Flag, flag_id)
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    get_doctor(user, db)
    rows = (
        db.query(GuestJudgeInvite)
        .filter(GuestJudgeInvite.flag_id == flag.id)
        .order_by(GuestJudgeInvite.id.desc())
        .all()
    )
    return {
        "flag_id": flag.id,
        "pool": internal_pool_status(db, flag),
        "invites": [
            guest_invite_public(row, include_token=(row.invited_by_id == user.id and row.status in {"invited", "accessed"}))
            for row in rows
        ],
    }


@router.get("/guest-judge/{token}")
def guest_judge_status(token: str, db: Session = Depends(get_db)):
    expire_guest_invites(db)
    try:
        invite = load_guest_invite(db, token)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if invite.status == "expired":
        db.commit()
        raise HTTPException(status_code=410, detail="This guest invite has expired")
    mark_guest_accessed(db, invite)
    db.commit()
    db.refresh(invite)
    return _guest_case_payload(invite)


@router.get("/guest-judge/{token}/prefill")
def guest_judge_prefill(token: str, db: Session = Depends(get_db)):
    try:
        invite = load_guest_invite(db, token)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return guest_invite_prefill(invite)


@router.post("/guest-judge/{token}/verify-license")
def guest_judge_verify_license(token: str, body: GuestLicenseRequest, db: Session = Depends(get_db)):
    try:
        invite = access_guest_invite(db, token, body.license_number)
    except ValueError as exc:
        detail = str(exc)
        code = 410 if "expired" in detail.lower() else 403
        if "not found" in detail.lower():
            code = 404
        raise HTTPException(status_code=code, detail=detail) from exc
    db.commit()
    db.refresh(invite)
    return _guest_case_payload(invite)


@router.post("/guest-judge/{token}/judge")
def guest_judge_submit(token: str, body: GuestJudgmentRequest, db: Session = Depends(get_db)):
    try:
        invite = submit_guest_judgment(db, token, choice=body.choice, explanation=body.explanation)
    except ValueError as exc:
        detail = str(exc)
        code = 400
        if "expired" in detail.lower():
            code = 410
        elif "not found" in detail.lower():
            code = 404
        raise HTTPException(status_code=code, detail=detail) from exc
    db.commit()
    db.refresh(invite)
    payload = _guest_case_payload(invite)
    payload["signup_path"] = f"/doctor/signup?prefill_token={invite.invite_token}"
    return payload


@router.post("/doctor/signup")
def doctor_signup(body: DoctorSignupRequest, db: Session = Depends(get_db)):
    try:
        user, _doctor, _invite = complete_doctor_signup_from_invite(
            db,
            name=body.name,
            email=body.email,
            password=body.password,
            specialty=body.specialty,
            hospital=body.hospital,
            license_number=body.license_number,
            date_of_birth=body.date_of_birth,
            qualification_score=body.qualification_score,
            years_experience=body.years_experience,
            research_count=body.research_count,
            prefill_token=body.prefill_token,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(user)
    return me_payload(user, None, None)


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
    approved = (
        db.query(AccessRequest)
        .filter(AccessRequest.patient_id == patient.id, AccessRequest.status == "approved")
        .all()
    )
    msg = (
        f"{user.name} suggested a correction to {patient.user.name}'s {body.field}: "
        f"{item.proposed_value}"
    )
    for req in approved:
        notify(db, req.doctor.user_id, "correction_submitted", msg, item.id)
    db.commit()
    db.refresh(item)
    return correction_public(item)
