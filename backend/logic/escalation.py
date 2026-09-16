"""Flag escalation: dynamic resolution deadlines and third-doctor selection."""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Diagnosis, Doctor, Flag, JudgeDecline, Patient

LOW_RESOLUTION_HOURS = 72
MEDIUM_RESOLUTION_HOURS = 36
LINGERING_CONFLICT_DAYS = 14
MEDICATION_URGENCY_FACTOR = 0.75
LINGERING_CONFLICT_FACTOR = 0.85
RESOLUTION_CREDIBILITY_BOOST = 0.1
CREDIBILITY_SCORE_CAP = 10.0

LABEL_SPECIALTIES = {
    "hypertension": ("cardiology", "internal medicine"),
    "type 2 diabetes": ("endocrinology", "internal medicine"),
    "migraine": ("neurology",),
    "asthma": ("pulmonology", "internal medicine"),
    "anxiety disorder": ("psychiatry", "neurology"),
    "hypothyroidism": ("endocrinology", "internal medicine"),
    "coronary artery disease": ("cardiology", "internal medicine"),
    "anemia": ("hematology", "internal medicine"),
    "gerd": ("gastroenterology", "internal medicine"),
    "lower back pain": ("orthopedics", "neurology", "internal medicine"),
}

MEDICATION_HINTS = {
    "hypertension": ("amlodipine", "lisinopril", "losartan", "atenolol", "hydrochlorothiazide"),
    "type 2 diabetes": ("metformin", "insulin", "glipizide", "empagliflozin"),
    "migraine": ("sumatriptan", "propranolol", "topiramate"),
    "asthma": ("albuterol", "salbutamol", "fluticasone", "montelukast"),
    "anxiety disorder": ("sertraline", "escitalopram", "buspirone"),
    "hypothyroidism": ("levothyroxine",),
    "coronary artery disease": ("atorvastatin", "clopidogrel", "aspirin", "metoprolol"),
    "anemia": ("ferrous", "iron"),
    "gerd": ("omeprazole", "pantoprazole"),
    "lower back pain": ("ibuprofen", "naproxen", "gabapentin"),
}


def _tokens(text: str) -> set[str]:
    return {part for part in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(part) > 2}


def _label_key(label: str) -> str:
    return re.sub(r"\s+", " ", (label or "").strip().lower())


def _patient_has_tied_medication(patient: Patient | None, labels: list[str]) -> bool:
    if not patient:
        return False
    meds = " ".join(str(item) for item in (patient.medications or [])).lower()
    if not meds:
        return False
    for label in labels:
        key = _label_key(label)
        hints = MEDICATION_HINTS.get(key, ())
        if any(hint in meds for hint in hints):
            return True
        if any(token in meds for token in _tokens(label)):
            return True
    return False


def _diagnoses_lingered(dx_a: Diagnosis | None, dx_b: Diagnosis | None) -> bool:
    if not dx_a or not dx_b or not dx_a.timestamp or not dx_b.timestamp:
        return False
    gap = abs((dx_a.timestamp - dx_b.timestamp).days)
    return gap > LINGERING_CONFLICT_DAYS


def calculate_resolution_deadline(flag: Flag) -> datetime | None:
    severity = (flag.severity or "").lower()
    if severity == "low":
        base_hours = LOW_RESOLUTION_HOURS
    elif severity == "medium":
        base_hours = MEDIUM_RESOLUTION_HOURS
    else:
        return None

    multiplier = 1.0
    labels = [
        flag.diagnosis_1.diagnosis_label if flag.diagnosis_1 else "",
        flag.diagnosis_2.diagnosis_label if flag.diagnosis_2 else "",
    ]
    if _patient_has_tied_medication(flag.patient, labels):
        multiplier *= MEDICATION_URGENCY_FACTOR
    if _diagnoses_lingered(flag.diagnosis_1, flag.diagnosis_2):
        multiplier *= LINGERING_CONFLICT_FACTOR
    return datetime.now() + timedelta(hours=base_hours * multiplier)


def calculate_credibility_score(doctor: Doctor) -> float:
    """Base credentials plus resolved-case boosts only. Never reduced for declines."""
    resolved = getattr(doctor, "resolved_cases_count", 0) or 0
    base = (
        doctor.qualification_score * 0.4
        + min(doctor.years_experience / 20, 1) * 10 * 0.3
        + min(doctor.research_count / 10, 1) * 10 * 0.3
    )
    return min(base + resolved * RESOLUTION_CREDIBILITY_BOOST, CREDIBILITY_SCORE_CAP)


def refresh_credibility_score(doctor: Doctor) -> float:
    computed = round(calculate_credibility_score(doctor), 4)
    current = doctor.credibility_score or 0.0
    # credibility_score only ever increases. Do not overwrite a higher stored value.
    doctor.credibility_score = max(current, computed)
    return doctor.credibility_score


def credit_resolved_case(doctor: Doctor) -> float:
    """Increment resolved_cases_count and apply the small credibility boost, capped at 10."""
    doctor.resolved_cases_count = (doctor.resolved_cases_count or 0) + 1
    doctor.credibility_score = min(
        CREDIBILITY_SCORE_CAP,
        round((doctor.credibility_score or 0.0) + RESOLUTION_CREDIBILITY_BOOST, 4),
    )
    return doctor.credibility_score


def _specialties_for_flag(flag: Flag) -> set[str]:
    wanted: set[str] = set()
    for dx in (flag.diagnosis_1, flag.diagnosis_2):
        if not dx:
            continue
        wanted.update(LABEL_SPECIALTIES.get(_label_key(dx.diagnosis_label), ()))
    return wanted


def _specialty_matches(doctor: Doctor, wanted: set[str]) -> bool:
    spec = (doctor.specialty or "").strip().lower()
    if not spec:
        return False
    if not wanted:
        return True
    if spec in wanted:
        return True
    return any(spec in item or item in spec for item in wanted)


def _declined_doctor_ids(db: Session, flag: Flag) -> set[int]:
    return {
        row.doctor_id
        for row in db.query(JudgeDecline).filter(JudgeDecline.flag_id == flag.id).all()
    }


def specialty_matched_third_doctors(db: Session, flag: Flag) -> list[Doctor]:
    """Third-doctor candidates whose specialty is relevant. No all-doctor fallback."""
    wanted = _specialties_for_flag(flag)
    pool = matching_third_doctors(db, flag, exclude_declined=True)
    if not wanted:
        return pool
    return [doctor for doctor in pool if _specialty_matches(doctor, wanted)]


def matching_third_doctors(db: Session, flag: Flag, *, exclude_declined: bool = True) -> list[Doctor]:
    involved = {flag.diagnosis_1.doctor_id, flag.diagnosis_2.doctor_id}
    declined = _declined_doctor_ids(db, flag) if exclude_declined else set()
    wanted = _specialties_for_flag(flag)
    doctors = db.query(Doctor).all()
    eligible = []
    for doctor in doctors:
        if doctor.id in involved or doctor.id in declined:
            continue
        refresh_credibility_score(doctor)
        if _specialty_matches(doctor, wanted):
            eligible.append(doctor)
    if not eligible:
        eligible = [d for d in doctors if d.id not in involved and d.id not in declined]
        for doctor in eligible:
            refresh_credibility_score(doctor)
    eligible.sort(key=lambda d: d.credibility_score, reverse=True)
    return eligible


def _notify(db: Session, user_id: int, ntype: str, message: str, related_id: int | None) -> None:
    from app.flagging import notify

    notify(db, user_id, ntype, message, related_id)


def _assign_doctor(db: Session, flag: Flag, doctor: Doctor) -> Doctor:
    flag.assigned_doctor_id = doctor.id
    flag.judge_pool_open = False
    flag.status = "escalated"
    patient_name = flag.patient.user.name if flag.patient and flag.patient.user else "a patient"
    _notify(
        db,
        doctor.user_id,
        "flag_judge_assigned",
        (
            f"You were assigned as the reviewing doctor for a flagged diagnosis gap "
            f"for {patient_name}. This is a suggestion, not a verdict."
        ),
        flag.id,
    )
    return doctor


def select_third_doctor(db: Session, flag: Flag, *, expired: bool = False) -> Doctor | list[Doctor] | None:
    pool = matching_third_doctors(db, flag)
    if not pool:
        return None
    severity = (flag.severity or "").lower()
    auto_assign = severity == "critical" or expired
    if auto_assign:
        return _assign_doctor(db, flag, pool[0])

    if severity == "high":
        if flag.assigned_doctor_id:
            return db.get(Doctor, flag.assigned_doctor_id)
        flag.judge_pool_open = True
        flag.status = "escalated"
        patient_name = flag.patient.user.name if flag.patient and flag.patient.user else "a patient"
        for doctor in pool:
            _notify(
                db,
                doctor.user_id,
                "flag_judge_invite",
                (
                    f"A high-severity diagnosis gap for {patient_name} needs a reviewing doctor. "
                    "Accept to judge if you can take this review. The first doctor to accept is assigned."
                ),
                flag.id,
            )
        return pool
    return pool


def apply_flag_escalation_on_create(db: Session, flag: Flag) -> None:
    severity = (flag.severity or "").lower()
    if severity in {"low", "medium"}:
        flag.resolution_deadline = calculate_resolution_deadline(flag)
        return
    if severity in {"high", "critical"}:
        select_third_doctor(db, flag)


def check_expired_flags(db: Session) -> list[Flag]:
    now = datetime.now()
    rows = (
        db.query(Flag)
        .filter(
            Flag.severity.in_(("low", "medium")),
            Flag.status.in_(("open", "under_review")),
            Flag.resolution_deadline.isnot(None),
            Flag.resolution_deadline <= now,
        )
        .all()
    )
    escalated: list[Flag] = []
    for flag in rows:
        flag.status = "escalated"
        select_third_doctor(db, flag, expired=True)
        escalated.append(flag)
    return escalated


def accept_flag_to_judge(db: Session, flag: Flag, doctor: Doctor) -> Flag:
    if flag.assigned_doctor_id:
        raise ValueError("This flag already has a reviewing doctor.")
    if not flag.judge_pool_open and (flag.severity or "").lower() != "high" and flag.status != "escalated":
        raise ValueError("This flag is not open for a reviewing doctor.")
    involved = {flag.diagnosis_1.doctor_id, flag.diagnosis_2.doctor_id}
    if doctor.id in involved:
        raise ValueError("Doctors already on this flag cannot accept to judge it.")
    pool_ids = {item.id for item in matching_third_doctors(db, flag, exclude_declined=False)}
    if pool_ids and doctor.id not in pool_ids:
        raise ValueError("Your specialty is not in the review pool for this flag.")
    _assign_doctor(db, flag, doctor)
    return flag


def decline_judge(db: Session, flag_id: int, doctor_id: int) -> JudgeDecline:
    """Log that this doctor declined to judge. Does not modify credibility_score.

    Intentional by design: declining or ignoring a High-severity open-pool invite
    or a Critical auto-assignment has no effect on credibility_score. There is
    no decrement path for non-participation anywhere in this module.
    """
    flag = db.get(Flag, flag_id)
    doctor = db.get(Doctor, doctor_id)
    if not flag:
        raise ValueError("Flag not found.")
    if not doctor:
        raise ValueError("Doctor not found.")
    if flag.status == "resolved":
        raise ValueError("This flag is already resolved.")

    existing = (
        db.query(JudgeDecline)
        .filter(JudgeDecline.flag_id == flag.id, JudgeDecline.doctor_id == doctor.id)
        .first()
    )
    if existing:
        return existing

    record = JudgeDecline(flag_id=flag.id, doctor_id=doctor.id)
    db.add(record)

    if flag.assigned_doctor_id == doctor.id:
        flag.assigned_doctor_id = None
        severity = (flag.severity or "").lower()
        if severity == "high":
            flag.judge_pool_open = True
        else:
            select_third_doctor(db, flag, expired=True)

    _notify(
        db,
        doctor.user_id,
        "flag_judge_declined",
        "Your decision not to judge this flag was recorded. Credibility is unchanged.",
        flag.id,
    )
    return record


def credit_resolver_if_reviewing(flag: Flag, doctor: Doctor) -> None:
    """Boost credibility only when the assigned 2nd/3rd reviewing doctor resolves."""
    if doctor.id != flag.assigned_doctor_id:
        return
    credit_resolved_case(doctor)
