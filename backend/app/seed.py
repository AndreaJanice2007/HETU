from sqlalchemy.orm import Session

from app.models import (
    AccessRequest,
    ConversationNote,
    CorrectionSuggestion,
    Diagnosis,
    Doctor,
    DoctorAvailability,
    DoctorConversation,
    Flag,
    GuestJudgeInvite,
    JudgeDecline,
    MedicalReport,
    Notification,
    Patient,
    Surrogate,
    User,
)


def _is_demo_email(email: str) -> bool:
    return (email or "").strip().lower().endswith("@hetu.demo")


def purge_clinical_rows(db: Session) -> None:
    for model in (
        ConversationNote,
        DoctorAvailability,
        DoctorConversation,
        MedicalReport,
        GuestJudgeInvite,
        JudgeDecline,
        Flag,
        Diagnosis,
        Notification,
        CorrectionSuggestion,
        AccessRequest,
    ):
        db.query(model).delete(synchronize_session=False)
    for patient in db.query(Patient).all():
        patient.conditions = []
        patient.medications = []
        patient.surrogate_id = None


def _delete_users(db: Session, users: list[User]) -> None:
    if not users:
        db.flush()
        db.commit()
        return

    user_ids = [user.id for user in users]
    doctor_ids = [row.id for row in db.query(Doctor).filter(Doctor.user_id.in_(user_ids)).all()]
    patient_ids = [row.id for row in db.query(Patient).filter(Patient.user_id.in_(user_ids)).all()]
    surrogate_ids = [row.id for row in db.query(Surrogate).filter(Surrogate.user_id.in_(user_ids)).all()]

    purge_clinical_rows(db)

    if patient_ids:
        for patient in db.query(Patient).filter(Patient.id.in_(patient_ids)).all():
            patient.surrogate_id = None
        db.flush()
        db.query(Surrogate).filter(Surrogate.linked_patient_id.in_(patient_ids)).delete(synchronize_session=False)
        db.query(Patient).filter(Patient.id.in_(patient_ids)).delete(synchronize_session=False)
    if surrogate_ids:
        db.query(Surrogate).filter(Surrogate.id.in_(surrogate_ids)).delete(synchronize_session=False)
    if doctor_ids:
        db.query(Doctor).filter(Doctor.id.in_(doctor_ids)).delete(synchronize_session=False)
    db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
    db.commit()


def purge_demo_accounts(db: Session) -> None:
    """Remove leftover seeded @hetu.demo logins. User-created accounts stay."""
    _delete_users(db, [user for user in db.query(User).all() if _is_demo_email(user.email)])


def wipe_all_accounts(db: Session) -> None:
    """Empty the directory so Sign up can start from a blank app."""
    _delete_users(db, db.query(User).all())
