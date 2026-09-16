"""OpenAI-backed diagnosis conflict detection.

Uses the same OpenAI client and model as Medrea. Root-cause labels stay heuristic.
Never print or hard-code API keys.
"""

from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy.orm import Session

from app.age import age_from_dob
from app.models import Diagnosis, Flag, Patient
from logic.openai_util import chat_json

ALLOWED_SEVERITIES = {"low", "medium", "high", "critical"}

CONFLICT_PROMPT = """You are a clinical reconciliation assistant. Compare these two diagnoses for the same patient and determine if they conflict.

Diagnosis 1 (Dr. {old_doctor}, {old_date}): "{old_label}" — {old_text}

Diagnosis 2 (Dr. {new_doctor}, {new_date}): "{new_label}" — {new_text}

Patient context: {patient_context}

Respond ONLY in this exact JSON format, no other text:
{{
  "conflict_detected": true or false,
  "severity": "low" or "medium" or "high" or "critical",
  "reasoning": "one plain-language sentence explaining why this severity level, written neutrally without blaming either doctor"
}}

Rules:
- If the two diagnosis labels are different names (not spelling or synonyms of the same condition), set conflict_detected to true. Coexisting conditions such as hypertension and diabetes are still a difference to review.
- Use severity for urgency, not to hide the difference: low = often coexist or minor wording; medium = related but different; high = unrelated categories; critical = life-threatening mismatch or medication conflict.
- Set conflict_detected to false only when the labels mean the same condition.

Severity guide:
- critical: one diagnosis is life-threatening and the other misses it entirely, OR an active medication conflicts with the alternate diagnosis
- high: diagnoses are in completely unrelated categories, or suggest a missed cross-specialty connection
- medium: diagnoses are related but meaningfully different (e.g., viral vs bacterial)
- low: minor wording differences, or two conditions that often coexist

Do not diagnose the patient. Do not say which doctor is correct. Flags are suggestions.
"""

FALLBACK_RESULT = {
    "conflict_detected": True,
    "severity": "medium",
    "reasoning": (
        "Automated comparison was unavailable, so this pair is held for clinician review. "
        "This is a suggestion, not a verdict."
    ),
    "fallback": True,
}


def _dx_view(diagnosis: Diagnosis) -> SimpleNamespace:
    doctor = diagnosis.doctor
    name = doctor.user.name if doctor and doctor.user else "Unknown"
    return SimpleNamespace(
        id=diagnosis.id,
        doctor_name=name,
        date=diagnosis.timestamp.isoformat(sep=" ", timespec="minutes") if diagnosis.timestamp else "unknown date",
        diagnosis_label=diagnosis.diagnosis_label or "",
        full_text=diagnosis.full_notes or "(no notes)",
    )


def build_patient_context_summary(patient: Patient | None) -> str:
    if not patient or not patient.user:
        return "No additional patient context on file."
    age = age_from_dob(patient.user.date_of_birth)
    conditions = ", ".join(str(item) for item in (patient.conditions or []) if item) or "none listed"
    meds = ", ".join(str(item) for item in (patient.medications or []) if item) or "none listed"
    return f"Age {age}; known conditions: {conditions}; active medications: {meds}."


def classify_root_cause(new_diagnosis: Diagnosis, old_diagnosis: Diagnosis, patient_id: int | None = None) -> str:
    """Heuristic four-class label. Not a clinical verdict and not an LLM call."""
    del patient_id
    if (not new_diagnosis.disclose_to_patient) or (not old_diagnosis.disclose_to_patient):
        return "intentional_non_disclosure"
    notes = f"{new_diagnosis.full_notes or ''} {old_diagnosis.full_notes or ''}".lower()
    if any(
        phrase in notes
        for phrase in (
            "patient did not",
            "patient forgot",
            "not disclosed by",
            "declined to mention",
            "withheld by the patient",
        )
    ):
        return "patient_gap"
    if any(
        phrase in notes
        for phrase in (
            "serial",
            "interval change",
            "evolved",
            "repeat test",
            "later imaging",
            "follow-up study",
        )
    ):
        return "no_fault"
    return "doctor_gap"


def _normalize_result(payload: dict, *, fallback: bool = False) -> dict:
    severity = str(payload.get("severity") or "medium").strip().lower()
    if severity not in ALLOWED_SEVERITIES:
        severity = "medium"
    reasoning = str(payload.get("reasoning") or "").strip()
    if not reasoning:
        reasoning = FALLBACK_RESULT["reasoning"]
    detected = payload.get("conflict_detected")
    if isinstance(detected, str):
        detected = detected.strip().lower() in {"true", "yes", "1"}
    return {
        "conflict_detected": bool(detected),
        "severity": severity,
        "reasoning": reasoning,
        "fallback": fallback,
    }


def analyze_diagnosis_conflict(new_diagnosis, old_diagnosis, patient_context: str) -> dict:
    """Ask the same OpenAI path Medrea uses whether two diagnoses conflict."""
    new_view = _dx_view(new_diagnosis) if isinstance(new_diagnosis, Diagnosis) else new_diagnosis
    old_view = _dx_view(old_diagnosis) if isinstance(old_diagnosis, Diagnosis) else old_diagnosis
    prompt = CONFLICT_PROMPT.format(
        old_doctor=old_view.doctor_name,
        old_date=old_view.date,
        old_label=old_view.diagnosis_label,
        old_text=old_view.full_text,
        new_doctor=new_view.doctor_name,
        new_date=new_view.date,
        new_label=new_view.diagnosis_label,
        new_text=new_view.full_text,
        patient_context=patient_context or "No additional patient context on file.",
    )
    payload = chat_json(prompt)
    if not payload:
        return dict(FALLBACK_RESULT)
    return _normalize_result(payload)


def existing_open_flag(db: Session, diag_a_id: int, diag_b_id: int) -> Flag | None:
    pair = tuple(sorted((diag_a_id, diag_b_id)))
    flags = (
        db.query(Flag)
        .filter(Flag.status.in_(("open", "under_review", "pending_review", "escalated")))
        .all()
    )
    for flag in flags:
        if tuple(sorted((flag.diagnosis_id_1, flag.diagnosis_id_2))) == pair:
            return flag
    return None


def create_flag(
    db: Session,
    *,
    patient_id: int,
    diagnosis_id_1: int,
    diagnosis_id_2: int,
    severity: str,
    root_cause: str,
    ai_reasoning: str,
    status: str = "open",
) -> Flag:
    flag = Flag(
        patient_id=patient_id,
        diagnosis_id_1=diagnosis_id_1,
        diagnosis_id_2=diagnosis_id_2,
        status=status,
        severity=severity if severity in ALLOWED_SEVERITIES else "medium",
        root_cause=root_cause,
        ai_reasoning=ai_reasoning,
    )
    db.add(flag)
    db.flush()
    db.refresh(flag)
    return flag


def detect_conflicts(db: Session, new_diagnosis: Diagnosis) -> list[Flag]:
    patient = db.get(Patient, new_diagnosis.patient_id)
    others = (
        db.query(Diagnosis)
        .filter(
            Diagnosis.patient_id == new_diagnosis.patient_id,
            Diagnosis.doctor_id != new_diagnosis.doctor_id,
            Diagnosis.id != new_diagnosis.id,
        )
        .all()
    )
    context = build_patient_context_summary(patient)
    created: list[Flag] = []
    for old_diagnosis in others:
        if existing_open_flag(db, new_diagnosis.id, old_diagnosis.id):
            continue
        result = analyze_diagnosis_conflict(new_diagnosis, old_diagnosis, context)
        if not result.get("conflict_detected"):
            continue
        flag = create_flag(
            db,
            patient_id=new_diagnosis.patient_id,
            diagnosis_id_1=old_diagnosis.id,
            diagnosis_id_2=new_diagnosis.id,
            severity=result["severity"],
            root_cause=classify_root_cause(new_diagnosis, old_diagnosis, new_diagnosis.patient_id),
            ai_reasoning=result["reasoning"],
            status="pending_review" if result.get("fallback") else "open",
        )
        created.append(flag)
    return created


def check_for_flag(new_diagnosis: Diagnosis, patient_id: int, db: Session) -> Flag | None:
    del patient_id
    flags = detect_conflicts(db, new_diagnosis)
    return flags[0] if flags else None


def is_fallback_reasoning(text: str | None) -> bool:
    return (text or "").startswith("Automated comparison was unavailable")


def refresh_fallback_flags(db: Session) -> int:
    """Re-run model comparison for flags that only have the offline fallback sentence."""
    rows = db.query(Flag).all()
    updated = 0
    for flag in rows:
        if not is_fallback_reasoning(flag.ai_reasoning):
            continue
        patient = db.get(Patient, flag.patient_id)
        if not flag.diagnosis_1 or not flag.diagnosis_2:
            continue
        result = analyze_diagnosis_conflict(flag.diagnosis_2, flag.diagnosis_1, build_patient_context_summary(patient))
        if result.get("fallback"):
            continue
        flag.severity = result["severity"] if result["severity"] in ALLOWED_SEVERITIES else flag.severity
        flag.ai_reasoning = result["reasoning"]
        if flag.status == "pending_review":
            flag.status = "open"
        updated += 1
    return updated
