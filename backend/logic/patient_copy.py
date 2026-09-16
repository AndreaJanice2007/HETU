"""Patient-safe copy. Never surfaces raw severity labels."""

from __future__ import annotations

from app.models import Flag
from logic.openai_util import NO_CLINICAL_JUDGMENT, chat_text

FALLBACK_EXPLANATION = (
    "Two of your doctors wrote slightly different notes. They are looking at this "
    "together so your record stays clear. This is not an emergency message."
)

REWRITE_PROMPT = """Rewrite the following clinician-facing note into one or two calm sentences for a patient.

{no_judgment}

Do not use the words Critical, High, Medium, or Low.
Do not alarm the reader. Do not invent clinical facts.
Explain only that two notes differ and that the care team is reviewing them together.

Text:
{text}

Respond with only the rewritten sentences.
"""


def patient_status_label(severity: str | None, status: str | None) -> str:
    del severity  # never map into Critical/High/Medium/Low for patients
    status = (status or "").lower()
    if status == "resolved":
        return "This review is complete"
    if status == "escalated":
        return "A specialist is taking a closer look"
    return "Your doctors are looking at two notes together"


def patient_next_step(status: str | None) -> str:
    status = (status or "").lower()
    if status == "resolved":
        return "Your doctors have finished this review"
    if status == "escalated":
        return "A senior specialist is reviewing this"
    return "Your doctors are discussing this"


def rewrite_for_patient(ai_reasoning: str | None) -> str:
    text = (ai_reasoning or "").strip()
    if not text:
        return FALLBACK_EXPLANATION
    prompt = REWRITE_PROMPT.format(no_judgment=NO_CLINICAL_JUDGMENT, text=text)
    rewritten = chat_text(prompt)
    if not rewritten:
        return FALLBACK_EXPLANATION
    lowered = rewritten.lower()
    for banned in ("critical", "high severity", "medium severity", "low severity"):
        if banned in lowered:
            return FALLBACK_EXPLANATION
    return rewritten


def ensure_patient_explanation(flag: Flag) -> str:
    stored = (flag.patient_explanation or "").strip()
    if stored:
        return stored
    flag.patient_explanation = rewrite_for_patient(flag.ai_reasoning)
    return flag.patient_explanation


def conversation_patient_status(conversation) -> str:
    status = (conversation.status or "").lower()
    if status == "pending_schedule":
        return "Your doctors are reviewing this together"
    if status in {"scheduled", "in_progress"}:
        when = conversation.scheduled_time
        if when:
            stamp = when.strftime("%b %d, %Y at %H:%M")
            return f"A conversation has been scheduled for {stamp}"
        return "Your doctors are reviewing this together"
    if status == "completed":
        senior = conversation.senior_doctor
        if senior and senior.user:
            specialty = senior.specialty or "specialist"
            return f"Reviewed by {senior.user.name} ({specialty})"
        return "Your doctors have finished talking this through"
    return "Your doctors are reviewing this together"
