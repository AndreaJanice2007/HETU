"""External guest judges: token links, license checks, no Hetu signup."""

from __future__ import annotations

import re
import secrets
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Flag, GuestJudgeInvite, User
from logic.escalation import _specialties_for_flag, specialty_matched_third_doctors
from logic.verification import verify_license

GUEST_INVITE_HOURS = 72
MIN_INTERNAL_CREDIBILITY = 7.0
JUDGMENT_CHOICES = ("agree_a", "agree_b", "independent")

# Demo registry only — not a live medical-council lookup, and Hetu does not
# call external license APIs. Used to double-check well-known demo licenses.
DEMO_LICENSE_REGISTRY = {
    "nmcwb44821": {
        "name": "dr. anika bose",
        "specialty": "endocrinology",
        "display": "NMC/WB/44821",
    },
    "nmcka10288": {
        "name": "dr. vivek menon",
        "specialty": "pulmonology",
        "display": "NMC/KA/10288",
    },
}


def normalize_license(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def license_format_valid(value: str) -> bool:
    return len(normalize_license(value)) >= 6


def verify_guest_license(license_number: str, invite: GuestJudgeInvite) -> None:
    """Confirm the visitor holds the license named on this invite.

    Checks: recognizable license shape, exact match to the invite, and — when
    the number is in the demo registry — specialty consistency. Declining or
    failing this check does not affect any registered doctor's credibility.
    """
    if not license_format_valid(license_number):
        raise ValueError("That license number is not in a recognizable format.")
    if normalize_license(license_number) != normalize_license(invite.license_number):
        raise ValueError("License number does not match this invitation.")
    entry = DEMO_LICENSE_REGISTRY.get(normalize_license(license_number))
    if not entry:
        return
    spec = (invite.invited_specialty or "").strip().lower()
    registered = entry["specialty"]
    if spec and registered not in spec and spec not in registered:
        raise ValueError("This license is registered to a different specialty in the demo registry.")


def expire_guest_invites(db: Session, now: datetime | None = None) -> list[GuestJudgeInvite]:
    moment = now or datetime.now()
    rows = (
        db.query(GuestJudgeInvite)
        .filter(
            GuestJudgeInvite.status.in_(("invited", "accessed")),
            GuestJudgeInvite.expires_at <= moment,
        )
        .all()
    )
    for row in rows:
        row.status = "expired"
    return rows


def _touch_invite_expiry(invite: GuestJudgeInvite) -> GuestJudgeInvite:
    if invite.status in {"invited", "accessed"} and invite.expires_at <= datetime.now():
        invite.status = "expired"
    return invite


def internal_pool_status(db: Session, flag: Flag) -> dict:
    """True needs_guest_judge when no relevant in-pool doctor meets the bar."""
    wanted = _specialties_for_flag(flag)
    specialty_hits = specialty_matched_third_doctors(db, flag)
    qualified = [doctor for doctor in specialty_hits if (doctor.credibility_score or 0) >= MIN_INTERNAL_CREDIBILITY]
    if qualified:
        reason = "internal_pool_sufficient"
        needs = False
    elif not specialty_hits:
        reason = "no_relevant_specialty"
        needs = True
    else:
        reason = "below_credibility_bar"
        needs = True
    return {
        "needs_guest_judge": needs,
        "reason": reason,
        "min_credibility": MIN_INTERNAL_CREDIBILITY,
        "specialty_match_count": len(specialty_hits),
        "qualified_count": len(qualified),
        "wanted_specialties": sorted(wanted),
    }


def _new_token(db: Session) -> str:
    for _ in range(8):
        token = secrets.token_urlsafe(32)
        exists = db.query(GuestJudgeInvite).filter(GuestJudgeInvite.invite_token == token).first()
        if not exists:
            return token
    raise RuntimeError("Could not allocate a guest invite token.")


def create_guest_invite(
    db: Session,
    flag: Flag,
    inviter: User,
    *,
    invited_name: str,
    invited_email: str,
    invited_specialty: str,
    license_number: str,
) -> GuestJudgeInvite:
    if flag.status == "resolved":
        raise ValueError("This flag is already resolved.")
    name = (invited_name or "").strip()
    email = (invited_email or "").strip().lower()
    specialty = (invited_specialty or "").strip()
    license_value = (license_number or "").strip()
    if not name or not email or "@" not in email:
        raise ValueError("Guest name and a valid email are required.")
    if not specialty:
        raise ValueError("Guest specialty is required.")
    if not verify_license(license_value):
        raise ValueError("License number is required and must be in a recognizable format.")

    active = (
        db.query(GuestJudgeInvite)
        .filter(
            GuestJudgeInvite.flag_id == flag.id,
            GuestJudgeInvite.invited_email == email,
            GuestJudgeInvite.status.in_(("invited", "accessed")),
        )
        .first()
    )
    if active:
        raise ValueError("An active guest invite already exists for this email on this flag.")

    now = datetime.now()
    invite = GuestJudgeInvite(
        flag_id=flag.id,
        invited_name=name,
        invited_email=email,
        invited_specialty=specialty,
        license_number=license_value,
        invite_token=_new_token(db),
        status="invited",
        verified=True,
        invited_by_id=inviter.id,
        created_at=now,
        expires_at=now + timedelta(hours=GUEST_INVITE_HOURS),
    )
    db.add(invite)
    db.flush()
    return invite


def load_guest_invite(db: Session, token: str) -> GuestJudgeInvite:
    expire_guest_invites(db)
    invite = db.query(GuestJudgeInvite).filter(GuestJudgeInvite.invite_token == token).first()
    if not invite:
        raise ValueError("Invite not found.")
    _touch_invite_expiry(invite)
    return invite


def access_guest_invite(db: Session, token: str, license_number: str) -> GuestJudgeInvite:
    invite = load_guest_invite(db, token)
    if invite.status == "expired":
        raise ValueError("This guest invite has expired.")
    if invite.status == "judged":
        return invite
    if not verify_license(license_number):
        raise ValueError("That license number is not in a recognizable format.")
    verify_guest_license(license_number, invite)
    invite.verified = True
    if invite.status == "invited":
        invite.status = "accessed"
    db.flush()
    return invite


def mark_guest_accessed(db: Session, invite: GuestJudgeInvite) -> GuestJudgeInvite:
    if invite.status == "invited":
        invite.status = "accessed"
        db.flush()
    return invite


def submit_guest_judgment(
    db: Session,
    token: str,
    *,
    choice: str,
    explanation: str,
) -> GuestJudgeInvite:
    invite = load_guest_invite(db, token)
    if invite.status == "expired":
        raise ValueError("This guest invite has expired.")
    if invite.status == "judged":
        raise ValueError("This flag has already been judged.")
    picked = (choice or "").strip().lower()
    if picked not in JUDGMENT_CHOICES:
        raise ValueError("Choose whether you agree with Dr. A, Dr. B, or an independent diagnosis.")
    note = (explanation or "").strip()
    if len(note) < 3:
        raise ValueError("A written explanation is required.")
    flag = invite.flag
    if flag.status == "resolved":
        raise ValueError("This flag is already resolved.")
    label_a = flag.diagnosis_1.diagnosis_label if flag.diagnosis_1 else "Finding A"
    label_b = flag.diagnosis_2.diagnosis_label if flag.diagnosis_2 else "Finding B"
    if picked == "agree_a":
        summary = f"Agree with Dr. A ({label_a}). {note}"
    elif picked == "agree_b":
        summary = f"Agree with Dr. B ({label_b}). {note}"
    else:
        summary = f"Independent diagnosis. {note}"
    flag.status = "resolved"
    flag.resolution_note = summary
    flag.judge_pool_open = False
    invite.status = "judged"
    invite.judgment_choice = picked
    invite.judgment_explanation = note
    from app.flagging import notify, notify_flag_resolved

    notify_flag_resolved(db, flag)
    notify(
        db,
        invite.invited_by_id,
        "guest_judge_complete",
        (
            f"{invite.invited_name} submitted a guest review for {flag.patient.user.name}. "
            "This is a suggestion, not a verdict."
        ),
        flag.id,
    )
    db.flush()
    return invite


def complete_doctor_signup_from_invite(
    db: Session,
    *,
    name: str,
    email: str,
    password: str,
    specialty: str,
    hospital: str,
    license_number: str,
    date_of_birth,
    qualification_score: float = 0,
    years_experience: int = 0,
    research_count: int = 0,
    prefill_token: str | None = None,
):
    """Create a doctor account from a judged guest invite. Invite stays on the flag for audit."""
    from app.accounts import unique_username
    from app.models import Doctor
    from app.security import hash_password
    from logic.escalation import calculate_credibility_score

    if not verify_license(license_number):
        raise ValueError("License number is required and must be in a recognizable format.")
    cleaned_email = (email or "").strip().lower()
    if db.query(User).filter(User.email == cleaned_email).first():
        raise ValueError("An account with this email already exists.")
    if not prefill_token:
        raise ValueError("Guest invites are required to open a doctor profile this way.")
    invite = load_guest_invite(db, prefill_token)
    if invite.status != "judged":
        raise ValueError("Submit your guest judgment before creating a Hetu profile.")

    user = User(
        name=(name or "").strip(),
        username=unique_username(db, name or "", cleaned_email),
        email=cleaned_email,
        password_hash=hash_password(password),
        role="doctor",
        date_of_birth=date_of_birth,
    )
    db.add(user)
    db.flush()
    doctor = Doctor(
        user_id=user.id,
        specialty=(specialty or "").strip(),
        hospital=(hospital or "Independent practice").strip() or "Independent practice",
        qualification_score=float(qualification_score or 0),
        years_experience=int(years_experience or 0),
        research_count=int(research_count or 0),
        resolved_cases_count=1,
    )
    doctor.credibility_score = round(calculate_credibility_score(doctor), 4)
    db.add(doctor)
    db.flush()
    return user, doctor, invite
