"""Account helpers: unique usernames and identifier lookup."""

from __future__ import annotations

import re
from datetime import date

from sqlalchemy.orm import Session

from app.models import Doctor, Patient, Surrogate, User
from app.age import dob_from_age
from app.security import hash_password
from logic.escalation import calculate_credibility_score

DEFAULT_DOB = date(1990, 1, 1)


def slug_username(name: str, email: str = "") -> str:
    base = re.sub(r"[^a-z0-9]+", "", (name or "").lower())
    if not base:
        local = (email or "").split("@", 1)[0]
        base = re.sub(r"[^a-z0-9]+", "", local.lower()) or "user"
    return base[:40]


def unique_username(db: Session, name: str, email: str = "") -> str:
    base = slug_username(name, email)
    candidate = base
    n = 1
    while db.query(User).filter(User.username == candidate).first():
        n += 1
        candidate = f"{base}{n}"
    return candidate


def find_user_by_identifier(db: Session, raw: str) -> User | None:
    ident = (raw or "").strip()
    if not ident:
        return None
    if "@" in ident:
        return db.query(User).filter(User.email == ident.lower()).first()
    lowered = ident.lower()
    by_username = db.query(User).filter(User.username == lowered).first()
    if by_username:
        return by_username
    matches = [row for row in db.query(User).all() if (row.username or "").lower() == lowered]
    if matches:
        return matches[0]
    named = [row for row in db.query(User).all() if (row.name or "").strip().lower() == lowered]
    if len(named) == 1:
        return named[0]
    return None


def ensure_usernames(db: Session) -> None:
    for user in db.query(User).all():
        if user.username:
            continue
        user.username = unique_username(db, user.name, user.email)
        db.flush()


def create_user_account(
    db: Session,
    *,
    name: str,
    email: str,
    password: str,
    role: str,
    linked_patient_email: str | None = None,
    age: int | None = None,
    specialty: str | None = None,
    hospital: str | None = None,
    years_experience: int = 0,
) -> User:
    cleaned_email = email.strip().lower()
    cleaned_name = name.strip()
    if db.query(User).filter(User.email == cleaned_email).first():
        raise ValueError("An account with this email already exists.")
    born = dob_from_age(age) if age is not None else DEFAULT_DOB
    user = User(
        name=cleaned_name,
        username=unique_username(db, cleaned_name, cleaned_email),
        email=cleaned_email,
        password_hash=hash_password(password),
        role=role,
        date_of_birth=born,
    )
    db.add(user)
    db.flush()
    if role == "patient":
        db.add(Patient(user_id=user.id, conditions=[], medications=[]))
    elif role == "doctor":
        doctor = Doctor(
            user_id=user.id,
            specialty=(specialty or "General").strip() or "General",
            hospital=(hospital or "Independent practice").strip() or "Independent practice",
            qualification_score=0,
            years_experience=max(0, int(years_experience or 0)),
            research_count=0,
            resolved_cases_count=0,
        )
        doctor.credibility_score = round(calculate_credibility_score(doctor), 4)
        db.add(doctor)
    elif role == "surrogate":
        linked_email = (linked_patient_email or "").strip().lower()
        linked_user = db.query(User).filter(User.email == linked_email, User.role == "patient").first()
        if not linked_user or not linked_user.patient:
            raise ValueError("Enter the email of an existing patient to link this surrogate account.")
        db.add(
            Surrogate(
                user_id=user.id,
                linked_patient_id=linked_user.patient.id,
                relationship="Surrogate",
            )
        )
        db.flush()
        surrogate = db.query(Surrogate).filter(Surrogate.user_id == user.id).first()
        if surrogate:
            linked_user.patient.surrogate_id = surrogate.id
    else:
        raise ValueError("Role must be patient, doctor, or surrogate.")
    db.flush()
    return user
