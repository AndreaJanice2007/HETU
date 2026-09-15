"""Medrea — in-app help. Explains Hetu. Does not diagnose."""

from __future__ import annotations


DISCLAIMER = (
    "Medrea helps you use Hetu. It does not diagnose, rank, or treat any condition. "
    "Flags are suggestions. Final judgment always stays with the doctor."
)


def _last_user_text(messages: list) -> str:
    for item in reversed(messages or []):
        if (item.get("role") or "").lower() == "user":
            return (item.get("content") or "").strip()
    return ""


def reply_to(messages: list, report: dict | None = None) -> str:
    if report:
        return _report_reply(report)

    text = _last_user_text(messages).lower()
    if not text:
        return (
            "I'm Medrea. Ask how Hetu works — flags, consent, diagnoses, or minor accounts. "
            + DISCLAIMER
        )

    if any(word in text for word in ("flag", "mismatch", "gap", "conflict", "discrep")):
        return (
            "A flag appears when two doctors record different diagnosis labels for the same patient. "
            "Doctors see the labels right away. Patients and surrogates only see “pending review” until "
            "a doctor resolves the flag with a note. Hetu does not decide who is right. "
            + DISCLAIMER
        )
    if any(word in text for word in ("consent", "access", "approv", "deny")):
        return (
            "A doctor must request access. An adult patient approves or denies it. For a minor, the "
            "surrogate does that. Until access is approved, the doctor cannot log a diagnosis. "
            + DISCLAIMER
        )
    if any(word in text for word in ("minor", "child", "under 18", "view-only", "view only")):
        return (
            "Patients under 18 have view-only accounts. They can read records, notifications, and "
            "explanations, but cannot suggest corrections or approve access. The linked surrogate "
            "handles those write-actions. "
            + DISCLAIMER
        )
    if any(word in text for word in ("surrogate", "parent", "guardian")):
        return (
            "A surrogate is linked to one patient — a parent of a minor, or an adult’s designated "
            "contact. They receive full detail when a doctor chooses to notify the surrogate instead "
            "of disclosing directly to the patient. "
            + DISCLAIMER
        )
    if any(word in text for word in ("diagnos", "log", "label", "disclose")):
        return (
            "Doctors pick a structured diagnosis label, add notes, and choose whether to disclose to "
            "the patient. If disclosure is off, the surrogate can be notified instead. Hetu then "
            "compares labels across doctors. "
            + DISCLAIMER
        )
    if any(word in text for word in ("correct", "medication", "condition")):
        return (
            "Adult patients and surrogates can suggest corrections to conditions or medications. "
            "Those suggestions are stored for review. Minors cannot submit them. "
            + DISCLAIMER
        )
    if any(word in text for word in ("hello", "hi ", "hey", "help", "what can")):
        return (
            "I can explain flags, consent, logging a diagnosis, and minor vs surrogate roles. "
            "You can also Send report from a dashboard and choose Medrea to share a summary here. "
            + DISCLAIMER
        )
    return (
        "I can help with how Hetu works: flags, doctor access, diagnoses, and who can take "
        "write-actions. Ask about one of those, or send a report from your dashboard. "
        + DISCLAIMER
    )


def _report_reply(report: dict) -> str:
    name = report.get("patient_name") or "this patient"
    role = report.get("role") or "user"
    dx = report.get("diagnoses") or []
    flags = report.get("flags") or []
    open_flags = [f for f in flags if f.get("status") != "resolved"]
    resolved = [f for f in flags if f.get("status") == "resolved"]
    labels = [d.get("diagnosis_label") for d in dx if d.get("diagnosis_label")]
    label_bit = ", ".join(labels) if labels else "no disclosed labels in this summary"
    flag_bit = (
        f"{len(open_flags)} open flag(s) and {len(resolved)} resolved."
        if flags
        else "no flags in this summary."
    )
    return (
        f"I received a report from the {role} view for {name}. "
        f"On file: {label_bit}. Flag status: {flag_bit} "
        "This is a process summary only — I am not adding a diagnosis or choosing between doctors. "
        + DISCLAIMER
    )
