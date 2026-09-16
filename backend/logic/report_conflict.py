"""Duplicate-report conflict detection and doctor conversation flow.

OpenAI is used only for topical matching, duration estimation, and senior-doctor
selection. It must never diagnose or declare a doctor right or wrong.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Doctor, DoctorAvailability, DoctorConversation, MedicalReport, Notification, Patient
from logic.openai_util import NO_CLINICAL_JUDGMENT, chat_json, chat_text
from logic.patient_copy import rewrite_for_patient

BLOCK_ORDER = ("morning", "afternoon", "evening")
BLOCK_HOURS = {"morning": 9, "afternoon": 13, "evening": 17}
DEFAULT_DURATION_MINUTES = 30
CREDIBILITY_SCORE_CAP = 10.0
SCHEDULE_HOURS = 48


def _notify(db: Session, user_id: int, ntype: str, message: str, related_id: int | None = None) -> None:
    db.add(
        Notification(
            user_id=user_id,
            type=ntype,
            message=message,
            related_id=related_id,
        )
    )


def _normalize_issue(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def is_same_issue(left: str, right: str) -> bool:
    """Cheap topical overlap check. Not a diagnosis comparison."""
    a = _normalize_issue(left)
    b = _normalize_issue(right)
    if not a or not b:
        return False
    if a == b:
        return True
    tokens_a = {part for part in re.findall(r"[a-z0-9]+", a) if len(part) > 2}
    tokens_b = {part for part in re.findall(r"[a-z0-9]+", b) if len(part) > 2}
    if not tokens_a or not tokens_b:
        return False
    overlap = tokens_a & tokens_b
    return (len(overlap) / min(len(tokens_a), len(tokens_b))) >= 0.5


def openai_confirm_issue_match(issue_a: str, issue_b: str) -> bool:
    """Confirm topical match only. Never diagnose or judge treatment."""
    prompt = f"""Two medical reports were tagged with these related-issue labels:

Report A: "{issue_a}"
Report B: "{issue_b}"

Question: are these reports about the same underlying issue or symptom topic?

{NO_CLINICAL_JUDGMENT}
Do not compare treatment plans. Do not say which doctor is right.

Respond in JSON: {{"same_issue": true or false, "reason": "one short sentence about topic overlap only"}}
"""
    payload = chat_json(prompt)
    if not payload:
        return True
    value = payload.get("same_issue")
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1"}
    return bool(value)


def _treatment_text(report: MedicalReport) -> str:
    notes = (getattr(report, "notes", None) or "").strip()
    issue = (report.related_issue or "").strip()
    return notes or issue


def openai_confirm_treatment_diff(treatment_a: str, treatment_b: str) -> bool:
    """Confirm the written plans differ. Never say which treatment is better."""
    prompt = f"""Two doctors wrote these treatment or report notes for similar symptoms:

Doctor A: "{treatment_a}"
Doctor B: "{treatment_b}"

Question: are these different treatment approaches or plans?

{NO_CLINICAL_JUDGMENT}
Do not say which treatment is better. Do not diagnose.

Respond in JSON: {{"different_treatment": true or false, "reason": "one short sentence about plan difference only"}}
"""
    payload = chat_json(prompt)
    if not payload:
        return _normalize_issue(treatment_a) != _normalize_issue(treatment_b)
    value = payload.get("different_treatment")
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1"}
    return bool(value)


def treatments_differ(left: MedicalReport, right: MedicalReport) -> bool:
    a = _treatment_text(left)
    b = _treatment_text(right)
    if not a.strip() and not b.strip():
        return True
    if _normalize_issue(a) == _normalize_issue(b) and a.strip() and b.strip():
        return False
    return openai_confirm_treatment_diff(a, b)


def get_reports_for_patient(db: Session, patient_id: int, exclude_id: int | None = None) -> list[MedicalReport]:
    query = db.query(MedicalReport).filter(MedicalReport.patient_id == patient_id)
    if exclude_id:
        query = query.filter(MedicalReport.id != exclude_id)
    return query.order_by(MedicalReport.uploaded_at.asc(), MedicalReport.id.asc()).all()


def calculate_conversation_duration(issue_type: str) -> int:
    prompt = (
        f"For a medical issue of type '{issue_type}', estimate a reasonable discussion "
        "duration in minutes for two doctors to reconcile differing treatment approaches. "
        f"{NO_CLINICAL_JUDGMENT} "
        "Do not recommend a treatment. Respond with only a number (minutes), between 10 and 60."
    )
    try:
        raw = chat_text(prompt) or ""
        match = re.search(r"\d+", raw)
        minutes = int(match.group(0)) if match else DEFAULT_DURATION_MINUTES
    except (TypeError, ValueError):
        minutes = DEFAULT_DURATION_MINUTES
    return max(10, min(60, minutes or DEFAULT_DURATION_MINUTES))


def find_common_slot(doctor_1_availability: list, doctor_2_availability: list) -> str | None:
    """Return the earliest overlapping slot encoded as YYYY-MM-DD:block."""
    second = {str(item) for item in (doctor_2_availability or [])}

    def sort_key(slot: str):
        parts = str(slot).split(":")
        date_part = parts[0] if parts else ""
        block = parts[1] if len(parts) > 1 else "morning"
        order = BLOCK_ORDER.index(block) if block in BLOCK_ORDER else 9
        return (date_part, order)

    for slot in sorted((str(item) for item in (doctor_1_availability or [])), key=sort_key):
        if slot in second:
            return slot
    return None


def slot_to_datetime(slot: str) -> datetime:
    date_part, _, block = str(slot).partition(":")
    year, month, day = [int(part) for part in date_part.split("-")]
    hour = BLOCK_HOURS.get(block, 9)
    return datetime(year, month, day, hour, 0)


def _existing_conversation(db: Session, report_a_id: int, report_b_id: int) -> DoctorConversation | None:
    pair = tuple(sorted((report_a_id, report_b_id)))
    rows = db.query(DoctorConversation).all()
    for row in rows:
        if tuple(sorted((row.report_id_1, row.report_id_2))) == pair:
            return row
    return None


def create_conversation_request(
    db: Session,
    patient_id: int,
    doctor_id_1: int,
    doctor_id_2: int,
    old_report: MedicalReport,
    new_report: MedicalReport,
) -> DoctorConversation:
    existing = _existing_conversation(db, old_report.id, new_report.id)
    if existing:
        return existing
    issue_type = new_report.related_issue or old_report.related_issue or "unspecified"
    conversation = DoctorConversation(
        patient_id=patient_id,
        doctor_id_1=doctor_id_1,
        doctor_id_2=doctor_id_2,
        report_id_1=old_report.id,
        report_id_2=new_report.id,
        status="pending_schedule",
        duration_minutes=calculate_conversation_duration(issue_type),
        issue_type=issue_type,
        schedule_deadline=datetime.now() + timedelta(hours=SCHEDULE_HOURS),
    )
    db.add(conversation)
    db.flush()
    db.refresh(conversation)
    patient = db.get(Patient, patient_id)
    patient_name = patient.user.name if patient and patient.user else "the patient"
    doctor_1 = db.get(Doctor, doctor_id_1)
    doctor_2 = db.get(Doctor, doctor_id_2)
    deadline = conversation.schedule_deadline.strftime("%b %d, %Y %H:%M") if conversation.schedule_deadline else "soon"
    msg = (
        f"Similar symptoms with different treatment were found for {patient_name} ({issue_type}). "
        f"Please submit overlapping times within {SCHEDULE_HOURS} hours (by {deadline}). "
        "A senior doctor will join after a time is set. This is a coordination request, not a verdict."
    )
    if doctor_1:
        _notify(db, doctor_1.user_id, "conversation_requested", msg, conversation.id)
    if doctor_2:
        _notify(db, doctor_2.user_id, "conversation_requested", msg, conversation.id)
    if patient:
        _notify(
            db,
            patient.user_id,
            "conversation_requested",
            "Your doctors are reviewing this together. You will see an update when a time is set.",
            conversation.id,
        )
        if patient.surrogate:
            _notify(
                db,
                patient.surrogate.user_id,
                "conversation_requested",
                f"Doctors caring for {patient_name} are reviewing two reports together.",
                conversation.id,
            )
    return conversation


def check_duplicate_issue_reports(db: Session, patient_id: int, new_report: MedicalReport) -> DoctorConversation | None:
    if not new_report.doctor_id:
        return None
    existing_reports = get_reports_for_patient(db, patient_id, exclude_id=new_report.id)
    for old_report in reversed(existing_reports):
        if not old_report.doctor_id:
            continue
        if old_report.doctor_id == new_report.doctor_id:
            continue
        if not is_same_issue(old_report.related_issue, new_report.related_issue):
            continue
        match = openai_confirm_issue_match(old_report.related_issue, new_report.related_issue)
        if not match:
            continue
        if not treatments_differ(old_report, new_report):
            continue
        return create_conversation_request(
                db,
                patient_id,
                old_report.doctor_id,
                new_report.doctor_id,
                old_report,
                new_report,
            )
    return None


def try_schedule_conversation(db: Session, conversation: DoctorConversation) -> str | None:
    rows = {row.doctor_id: row for row in conversation.availabilities}
    first = rows.get(conversation.doctor_id_1)
    second = rows.get(conversation.doctor_id_2)
    if not first or not second:
        return None
    slot = find_common_slot(first.slots or [], second.slots or [])
    if not slot:
        patient = conversation.patient
        name = patient.user.name if patient and patient.user else "the patient"
        miss = (
            f"No overlapping time was found for the {name} conversation. "
            "Please submit different morning/afternoon/evening slots."
        )
        _notify(db, conversation.doctor_1.user_id, "conversation_requested", miss, conversation.id)
        _notify(db, conversation.doctor_2.user_id, "conversation_requested", miss, conversation.id)
        return None
    conversation.status = "scheduled"
    conversation.scheduled_time = slot_to_datetime(slot)
    when = conversation.scheduled_time.strftime("%b %d, %Y at %H:%M")
    confirm = (
        f"Conversation scheduled for {when} ({conversation.duration_minutes} minutes) "
        f"about '{conversation.issue_type}'."
    )
    _notify(db, conversation.doctor_1.user_id, "conversation_scheduled", confirm, conversation.id)
    _notify(db, conversation.doctor_2.user_id, "conversation_scheduled", confirm, conversation.id)
    patient = conversation.patient
    if patient:
        _notify(
            db,
            patient.user_id,
            "conversation_scheduled",
            f"A conversation has been scheduled for {when}.",
            conversation.id,
        )
        if patient.surrogate:
            _notify(
                db,
                patient.surrogate.user_id,
                "conversation_scheduled",
                f"A conversation for {patient.user.name} has been scheduled for {when}.",
                conversation.id,
            )
    escalate_to_senior(db, conversation)
    return slot


def _doctor_list_payload(doctors: list[Doctor]) -> list[dict]:
    payload = []
    for doctor in doctors:
        payload.append(
            {
                "doctor_id": doctor.id,
                "name": doctor.user.name if doctor.user else "",
                "specialty": doctor.specialty,
                "years_experience": doctor.years_experience or 0,
                "research_count": doctor.research_count or 0,
                "credibility_score": doctor.credibility_score or 0,
                "resolved_cases_count": doctor.resolved_cases_count or 0,
            }
        )
    return payload


def _specialty_match_score(doctor: Doctor, issue_type: str) -> int:
    specialty = (doctor.specialty or "").lower()
    issue = (issue_type or "").lower()
    if not specialty:
        return 0
    if specialty in issue or issue in specialty:
        return 2
    spec_tokens = {part for part in re.findall(r"[a-z0-9]+", specialty) if len(part) > 3}
    issue_tokens = {part for part in re.findall(r"[a-z0-9]+", issue) if len(part) > 3}
    return 1 if spec_tokens & issue_tokens else 0


def _fallback_senior(doctors: list[Doctor], issue_type: str) -> Doctor | None:
    if not doctors:
        return None
    return max(
        doctors,
        key=lambda doctor: (
            _specialty_match_score(doctor, issue_type),
            doctor.credibility_score or 0,
            doctor.years_experience or 0,
            doctor.research_count or 0,
        ),
    )


def select_senior_doctor(db: Session, conversation: DoctorConversation) -> Doctor | None:
    involved = {conversation.doctor_id_1, conversation.doctor_id_2}
    candidates = [doctor for doctor in db.query(Doctor).all() if doctor.id not in involved]
    if not candidates:
        return None
    prompt = f"""Given this list of doctors with their specialty, years of experience, and research count:
{_doctor_list_payload(candidates)}
And this treatment/issue type: {conversation.issue_type}

Select the single most qualified senior doctor to review this case.
{NO_CLINICAL_JUDGMENT}
Do not comment on which original doctor is correct. Selection is about seniority and specialty fit only.

Respond in JSON: {{"doctor_id": ..., "reasoning": "one sentence"}}
"""
    payload = chat_json(prompt)
    chosen = None
    if payload:
        try:
            chosen_id = int(payload.get("doctor_id"))
            chosen = next((doctor for doctor in candidates if doctor.id == chosen_id), None)
        except (TypeError, ValueError):
            chosen = None
    return chosen or _fallback_senior(candidates, conversation.issue_type)


def award_review_credibility(senior_doctor: Doctor) -> None:
    senior_doctor.resolved_cases_count = (senior_doctor.resolved_cases_count or 0) + 1
    senior_doctor.credibility_score = min(
        CREDIBILITY_SCORE_CAP,
        round((senior_doctor.credibility_score or 0) + 0.5, 4),
    )


def backfill_senior_review_credits(db: Session) -> None:
    rows = (
        db.query(DoctorConversation)
        .filter(
            DoctorConversation.status == "completed",
            DoctorConversation.senior_doctor_id.isnot(None),
        )
        .all()
    )
    counts: dict[int, int] = {}
    for row in rows:
        counts[row.senior_doctor_id] = counts.get(row.senior_doctor_id, 0) + 1
    changed = False
    for doctor_id, count in counts.items():
        doctor = db.get(Doctor, doctor_id)
        if not doctor:
            continue
        have = doctor.resolved_cases_count or 0
        if have >= count:
            continue
        for _ in range(count - have):
            award_review_credibility(doctor)
        changed = True
    if changed:
        db.commit()


def escalate_to_senior(db: Session, conversation: DoctorConversation) -> Doctor | None:
    senior = select_senior_doctor(db, conversation)
    if not senior:
        return None
    conversation.senior_doctor_id = senior.id
    conversation.status = "in_progress"
    patient = conversation.patient
    name = patient.user.name if patient and patient.user else "the patient"
    _notify(
        db,
        senior.user_id,
        "senior_review_assigned",
        (
            f"You were asked to review a doctor conversation for {name} "
            f"about '{conversation.issue_type}'. Please read both reports and the notes, "
            "then submit a final conclusion. This is a coordination review, not a diagnosis."
        ),
        conversation.id,
    )
    if patient:
        _notify(
            db,
            patient.user_id,
            "senior_review_assigned",
            "A senior specialist is reviewing this.",
            conversation.id,
        )
    return senior


def enforce_schedule_deadlines(db: Session) -> None:
    now = datetime.now()
    overdue = (
        db.query(DoctorConversation)
        .filter(
            DoctorConversation.status == "pending_schedule",
            DoctorConversation.schedule_deadline.isnot(None),
            DoctorConversation.schedule_deadline < now,
        )
        .all()
    )
    for conversation in overdue:
        if conversation.senior_doctor_id:
            conversation.status = "in_progress"
            continue
        senior = escalate_to_senior(db, conversation)
        if senior:
            _notify(
                db,
                conversation.doctor_1.user_id,
                "conversation_requested",
                "The scheduling window closed. A senior doctor is now reviewing.",
                conversation.id,
            )
            _notify(
                db,
                conversation.doctor_2.user_id,
                "conversation_requested",
                "The scheduling window closed. A senior doctor is now reviewing.",
                conversation.id,
            )


def complete_conversation(
    db: Session,
    conversation: DoctorConversation,
    *,
    conclusion: str,
    agreed: bool,
    acting_doctor: Doctor,
    good_treatment: bool = True,
) -> DoctorConversation:
    text = (conclusion or "").strip()
    conversation.conclusion = text
    notes = conversation.transcript_or_notes or ""
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    conversation.transcript_or_notes = (
        f"{notes}\n[{stamp}] {acting_doctor.user.name}: {text}".strip() if notes else f"[{stamp}] {acting_doctor.user.name}: {text}"
    )
    is_senior = conversation.senior_doctor_id == acting_doctor.id
    if agreed or is_senior:
        conversation.agreed = True if agreed else False
        conversation.status = "completed"
        conversation.patient_conclusion = rewrite_for_patient(text)
        patient = conversation.patient
        ntype = "senior_review_complete" if is_senior else "conversation_resolved"
        if is_senior:
            award_review_credibility(acting_doctor)
            doctor_msg = (
                f"Senior review complete for {patient.user.name if patient else 'the patient'}: {text}"
            )
            _notify(db, conversation.doctor_1.user_id, ntype, doctor_msg, conversation.id)
            _notify(db, conversation.doctor_2.user_id, ntype, doctor_msg, conversation.id)
        else:
            _notify(
                db,
                conversation.doctor_1.user_id,
                ntype,
                f"Conversation complete. Conclusion: {text}",
                conversation.id,
            )
            _notify(
                db,
                conversation.doctor_2.user_id,
                ntype,
                f"Conversation complete. Conclusion: {text}",
                conversation.id,
            )
        if patient:
            patient_msg = conversation.patient_conclusion or "Your doctors have finished talking this through."
            _notify(db, patient.user_id, ntype, patient_msg, conversation.id)
            if patient.surrogate:
                _notify(db, patient.surrogate.user_id, ntype, patient_msg, conversation.id)
        return conversation
    conversation.agreed = False
    escalate_to_senior(db, conversation)
    return conversation


def upsert_availability(
    db: Session,
    conversation: DoctorConversation,
    doctor: Doctor,
    slots: list[str],
) -> DoctorAvailability:
    row = (
        db.query(DoctorAvailability)
        .filter(
            DoctorAvailability.conversation_id == conversation.id,
            DoctorAvailability.doctor_id == doctor.id,
        )
        .first()
    )
    cleaned = [str(item) for item in slots if item]
    if row:
        row.slots = cleaned
        row.submitted_at = datetime.now()
    else:
        row = DoctorAvailability(conversation_id=conversation.id, doctor_id=doctor.id, slots=cleaned)
        db.add(row)
        db.flush()
    db.refresh(conversation)
    if conversation.status == "pending_schedule":
        try_schedule_conversation(db, conversation)
    return row
