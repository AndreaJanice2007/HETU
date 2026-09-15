from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.age import is_minor
from app.database import get_db
from app.models import AccessRequest, Doctor, Patient, Surrogate, User


def get_current_user(
    x_user_id: int | None = Header(default=None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> User:
    if x_user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not signed in")
    user = db.get(User, x_user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown user")
    return user


def require_role(*roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for this role")
        return user

    return checker


def get_doctor(user: User, db: Session) -> Doctor:
    if not user.doctor:
        doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()
    else:
        doctor = user.doctor
    if not doctor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Doctor profile required")
    return doctor


def get_patient_for_user(user: User, db: Session) -> Patient | None:
    if user.role == "patient":
        return db.query(Patient).filter(Patient.user_id == user.id).first()
    if user.role == "surrogate":
        surrogate = db.query(Surrogate).filter(Surrogate.user_id == user.id).first()
        if not surrogate:
            return None
        return db.get(Patient, surrogate.linked_patient_id)
    return None


def load_patient(db: Session, patient_id: int) -> Patient:
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return patient


def doctor_access_status(db: Session, doctor_id: int, patient_id: int) -> str | None:
    req = (
        db.query(AccessRequest)
        .filter(AccessRequest.doctor_id == doctor_id, AccessRequest.patient_id == patient_id)
        .order_by(AccessRequest.id.desc())
        .first()
    )
    return req.status if req else None


def require_doctor_access(db: Session, doctor: Doctor, patient: Patient) -> None:
    if doctor_access_status(db, doctor.id, patient.id) != "approved":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patient has not approved access",
        )


def can_write_for_patient(db: Session, user: User, patient: Patient) -> bool:
    if user.role == "patient":
        if patient.user_id != user.id:
            return False
        return not is_minor(user.date_of_birth)
    if user.role == "surrogate":
        surrogate = db.query(Surrogate).filter(Surrogate.user_id == user.id).first()
        return bool(surrogate and surrogate.linked_patient_id == patient.id)
    return False


def require_write_for_patient(db: Session, user: User, patient: Patient) -> None:
    if user.role == "patient" and patient.user_id == user.id and is_minor(user.date_of_birth):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Minor accounts are view-only. Your surrogate must take this action.",
        )
    if not can_write_for_patient(db, user, patient):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot change this record")


def can_view_patient(db: Session, user: User, patient: Patient) -> bool:
    if user.role == "patient":
        return patient.user_id == user.id
    if user.role == "surrogate":
        surrogate = db.query(Surrogate).filter(Surrogate.user_id == user.id).first()
        return bool(surrogate and surrogate.linked_patient_id == patient.id)
    if user.role == "doctor":
        doctor = get_doctor(user, db)
        return doctor_access_status(db, doctor.id, patient.id) == "approved"
    return False


def require_view_patient(db: Session, user: User, patient: Patient) -> None:
    if user.role == "doctor":
        doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()
        if doctor and doctor_access_status(db, doctor.id, patient.id) in ("approved", "pending"):
            return
        if doctor:
            # doctors may open a limited directory card without access
            return
    if not can_view_patient(db, user, patient) and user.role != "doctor":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot view this record")
