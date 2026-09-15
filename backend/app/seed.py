from datetime import date

from sqlalchemy.orm import Session

from app.catalog import DIAGNOSIS_LABELS
from app.models import (
    AccessRequest,
    Diagnosis,
    Doctor,
    Patient,
    Surrogate,
    User,
)
from app.security import hash_password

# Unique demo passwords — also documented in hetu/README.md
SEED_ACCOUNTS = [
    {
        "name": "Dr. Meera Sharma",
        "email": "meera.sharma@hetu.demo",
        "password": "MeeraApollo91",
        "role": "doctor",
        "date_of_birth": date(1978, 4, 11),
        "specialty": "Cardiology",
        "hospital": "Apollo",
    },
    {
        "name": "Dr. Arjun Patel",
        "email": "arjun.patel@hetu.demo",
        "password": "ArjunFortis44",
        "role": "doctor",
        "date_of_birth": date(1981, 9, 2),
        "specialty": "Neurology",
        "hospital": "Fortis",
    },
    {
        "name": "Priya Nair",
        "email": "priya.nair@hetu.demo",
        "password": "PriyaNair18",
        "role": "patient",
        "date_of_birth": date(1992, 3, 14),
        "conditions": ["Elevated blood pressure (self-reported)"],
        "medications": ["Amlodipine 5mg"],
    },
    {
        "name": "Ayaan Khan",
        "email": "ayaan.khan@hetu.demo",
        "password": "AyaanKhan12",
        "role": "patient",
        "date_of_birth": date(2014, 6, 21),
        "conditions": ["Seasonal allergies"],
        "medications": ["Cetirizine as needed"],
    },
    {
        "name": "Farah Khan",
        "email": "farah.khan@hetu.demo",
        "password": "FarahKhan27",
        "role": "surrogate",
        "date_of_birth": date(1986, 11, 3),
        "relationship": "Mother",
        "linked_patient_email": "ayaan.khan@hetu.demo",
    },
]


def seed_if_empty(db: Session) -> None:
    if db.query(User).first():
        return

    users_by_email: dict[str, User] = {}
    doctors_by_email: dict[str, Doctor] = {}
    patients_by_email: dict[str, Patient] = {}

    for row in SEED_ACCOUNTS:
        user = User(
            name=row["name"],
            email=row["email"].lower(),
            password_hash=hash_password(row["password"]),
            role=row["role"],
            date_of_birth=row["date_of_birth"],
        )
        db.add(user)
        db.flush()
        users_by_email[user.email] = user

        if row["role"] == "doctor":
            doctor = Doctor(
                user_id=user.id,
                specialty=row["specialty"],
                hospital=row["hospital"],
            )
            db.add(doctor)
            db.flush()
            doctors_by_email[user.email] = doctor

        if row["role"] == "patient":
            patient = Patient(
                user_id=user.id,
                conditions=row["conditions"],
                medications=row["medications"],
            )
            db.add(patient)
            db.flush()
            patients_by_email[user.email] = patient

    ayaan = patients_by_email["ayaan.khan@hetu.demo"]
    farah_row = next(r for r in SEED_ACCOUNTS if r["role"] == "surrogate")
    farah_user = users_by_email[farah_row["email"]]
    surrogate = Surrogate(
        user_id=farah_user.id,
        linked_patient_id=ayaan.id,
        relationship=farah_row["relationship"],
    )
    db.add(surrogate)
    db.flush()
    ayaan.surrogate_id = surrogate.id

    priya = patients_by_email["priya.nair@hetu.demo"]
    meera = doctors_by_email["meera.sharma@hetu.demo"]
    arjun = doctors_by_email["arjun.patel@hetu.demo"]

    db.add_all(
        [
            AccessRequest(doctor_id=meera.id, patient_id=priya.id, status="approved"),
            AccessRequest(doctor_id=arjun.id, patient_id=priya.id, status="approved"),
            AccessRequest(doctor_id=arjun.id, patient_id=ayaan.id, status="pending"),
        ]
    )
    db.add(
        Diagnosis(
            patient_id=priya.id,
            doctor_id=meera.id,
            diagnosis_label=DIAGNOSIS_LABELS[0],
            full_notes=(
                "Clinic BP 148/92. Lifestyle measures discussed. "
                "Follow-up in two weeks. Flag any conflicting neurology findings."
            ),
            disclose_to_patient=True,
        )
    )
    db.commit()
