from sqlalchemy.orm import Session

from app.age import is_minor
from app.models import Diagnosis, Flag, Notification, Patient
from logic.escalation import apply_flag_escalation_on_create
from logic.flag_detection import detect_conflicts


def notify(db: Session, user_id: int, ntype: str, message: str, related_id: int | None = None) -> None:
    db.add(
        Notification(
            user_id=user_id,
            type=ntype,
            message=message,
            related_id=related_id,
        )
    )


def evaluate_new_diagnosis(db: Session, diagnosis: Diagnosis) -> list[Flag]:
    """Compare a new diagnosis against other doctors' findings and raise flags."""
    patient = db.get(Patient, diagnosis.patient_id)
    created = detect_conflicts(db, diagnosis)
    for flag in created:
        apply_flag_escalation_on_create(db, flag)
        other = flag.diagnosis_1 if flag.diagnosis_id_2 == diagnosis.id else flag.diagnosis_2
        _notify_flag_raised(db, patient, flag, diagnosis, other)
    return created


def _notify_flag_raised(
    db: Session,
    patient: Patient,
    flag: Flag,
    new_dx: Diagnosis,
    other_dx: Diagnosis,
) -> None:
    doctor_msg = (
        f"Hetu flagged a possible diagnosis gap for {patient.user.name}: "
        f"'{other_dx.diagnosis_label}' vs '{new_dx.diagnosis_label}'. "
        "This is a suggestion, not a verdict."
    )
    notify(db, other_dx.doctor.user_id, "flag_raised", doctor_msg, flag.id)
    notify(db, new_dx.doctor.user_id, "flag_raised", doctor_msg, flag.id)

    pending_msg = (
        f"Hetu noticed that two of {patient.user.name}'s doctors recorded different findings. "
        "The doctors are reviewing this. No diagnostic detail is shown until a doctor resolves the flag."
    )
    patient_user = patient.user
    if is_minor(patient_user.date_of_birth):
        if patient.surrogate:
            notify(db, patient.surrogate.user_id, "flag_raised_pending", pending_msg, flag.id)
        notify(db, patient.user_id, "flag_raised_pending", pending_msg, flag.id)
    else:
        notify(db, patient.user_id, "flag_raised_pending", pending_msg, flag.id)


def notify_flag_resolved(db: Session, flag: Flag) -> None:
    patient = db.get(Patient, flag.patient_id)
    d1, d2 = flag.diagnosis_1, flag.diagnosis_2
    resolved_msg = (
        f"A doctor resolved the review for {patient.user.name}: "
        f"'{d1.diagnosis_label}' and '{d2.diagnosis_label}'. "
        "You can now read the full flag detail and the resolution note."
    )
    doctor_msg = (
        f"Flag for {patient.user.name} is resolved. "
        f"Note: {flag.resolution_note}"
    )
    notify(db, d1.doctor.user_id, "flag_resolved", doctor_msg, flag.id)
    notify(db, d2.doctor.user_id, "flag_resolved", doctor_msg, flag.id)
    if is_minor(patient.user.date_of_birth):
        notify(db, patient.user_id, "flag_resolved", resolved_msg, flag.id)
        if patient.surrogate:
            notify(db, patient.surrogate.user_id, "flag_resolved", resolved_msg, flag.id)
    else:
        notify(db, patient.user_id, "flag_resolved", resolved_msg, flag.id)


def notify_diagnosis_logged(db: Session, diagnosis: Diagnosis) -> None:
    patient = db.get(Patient, diagnosis.patient_id)
    doctor_name = diagnosis.doctor.user.name
    if diagnosis.disclose_to_patient:
        notify(
            db,
            patient.user_id,
            "diagnosis_disclosed",
            f"{doctor_name} recorded a disclosed diagnosis of {diagnosis.diagnosis_label}.",
            diagnosis.id,
        )
        return
    if patient.surrogate:
        notify(
            db,
            patient.surrogate.user_id,
            "diagnosis_to_surrogate",
            (
                f"{doctor_name} recorded a diagnosis of {diagnosis.diagnosis_label} "
                f"for {patient.user.name} and asked that the surrogate be notified "
                "instead of disclosing it directly to the patient. Notes: "
                f"{diagnosis.full_notes or '(none)'}"
            ),
            diagnosis.id,
        )
