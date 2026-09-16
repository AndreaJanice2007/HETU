"""Medrea — in-app assistant. Explains Hetu and general medical terms. Does not diagnose."""

from __future__ import annotations

from document_processor.openai_client import get_client, medrea_model

DISCLAIMER = (
    "Medrea helps you use Hetu. It does not diagnose, rank, or treat any condition. "
    "Flags are suggestions. Final judgment always stays with the doctor."
)

SYSTEM_PROMPT = """You are MEDREA, the in-app assistant for Hetu, a post-diagnosis reconciliation tool.

You can:
- Explain how Hetu works: flags when two doctors log different diagnosis labels, doctor access/consent, patient vs doctor vs surrogate roles, minors (view-only), Send report, and that flags are suggestions.
- Explain general medical terms, lab names, and conditions in plain language (for example what "anaemia" means in textbooks).
- Summarize extracted document fields that were provided to you.

You must not:
- Diagnose the user, say they have a disease, or recommend treatment as if you were their clinician.
- Rank which doctor is right.
- Invent diagnoses, symptoms, medications, laboratory values, or medical recommendations.
- Change clinical meaning in order to sound polished.

Formatting (the UI renders Markdown — do not write decorative symbols meant to be seen as plain text):
- Use real Markdown headings (## Section name), not a bold line pretending to be a heading.
- Put at most one emoji at the start of a section heading, only from: 🧠 🩺 🧪 💊 📋 🔍 ⚠️ 🚨 ✅ 💡 📌 📅 👤
- Typical clinical document replies use only the sections justified by the supplied text, for example:
  ## 🧠 Clinical Summary
  ## 🔍 Key Findings
  ## 💡 What This Means
  ## 📌 Important Context
  ## ⚠️ When to Follow Up  (only if the source material supports it)
- Short Hetu-how-it-works answers may use one ## 💡 heading and a short body.
- Short paragraphs. Bullet lists for findings.
- Bold **only** important medical terms, values, diagnoses, medications, and conclusions.
- Do not wrap an entire heading in **bold** instead of using ##.
- Do not use stacked ###, --- rules, or ASCII decoration.
- One emoji per section heading. Never an emoji on every sentence.
- End clinical answers with a brief reminder that MEDREA does not diagnose and a clinician decides.

Keep answers concise. Do not dump a lecture.
"""


def _last_user_text(messages: list) -> str:
    for item in reversed(messages or []):
        if (item.get("role") or "").lower() == "user":
            return (item.get("content") or "").strip()
    return ""


def reply_to(messages: list, report: dict | None = None) -> str:
    if report:
        return _report_reply(report)

    text = _last_user_text(messages)
    if not text:
        return (
            "I'm Medrea. Ask how Hetu works, or ask me to explain a medical term in plain language. "
            + DISCLAIMER
        )

    llm = _llm_reply(messages)
    if llm:
        return llm
    return _keyword_reply(text.lower())


def _llm_reply(messages: list) -> str | None:
    history = []
    for item in messages or []:
        role = (item.get("role") or "").lower()
        content = (item.get("content") or "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        history.append({"role": role, "content": content})
    if not history:
        return None
    history = history[-12:]
    try:
        client = get_client()
        response = client.responses.create(
            model=medrea_model(),
            instructions=SYSTEM_PROMPT,
            input=history,
        )
        text = (getattr(response, "output_text", None) or "").strip()
        return text or None
    except Exception:
        return None


def _keyword_reply(text: str) -> str:
    if any(word in text for word in ("flag", "mismatch", "gap", "conflict", "discrep")):
        return (
            "## 💡 How flags work\n\n"
            "A **flag** appears when two doctors record different **diagnosis labels** for the same patient. "
            "Doctors see the labels right away. Patients and surrogates only see “pending review” until "
            "a doctor resolves the flag with a note.\n\n"
            "Hetu does not decide who is right. Final judgment always stays with the doctor."
        )
    if any(word in text for word in ("consent", "access", "approv", "deny")):
        return (
            "## 💡 Access and consent\n\n"
            "A doctor must request **access**. An adult patient **approves** or **denies** it. For a **minor**, the "
            "surrogate does that. Until access is approved, the doctor cannot log a diagnosis."
        )
    if any(word in text for word in ("minor", "child", "under 18", "view-only", "view only")):
        return (
            "## 💡 Minor accounts\n\n"
            "Patients **under 18** have view-only accounts. They can read records, notifications, and "
            "explanations, but cannot suggest corrections or approve access. The linked **surrogate** "
            "handles those write-actions."
        )
    if any(word in text for word in ("surrogate", "parent", "guardian")):
        return (
            "## 👤 Surrogates\n\n"
            "A **surrogate** is linked to one patient — a parent of a minor, or an adult’s designated "
            "contact. They receive full detail when a doctor chooses to notify the surrogate instead "
            "of disclosing directly to the patient."
        )
    if any(word in text for word in ("hello", "hi ", "hey", "help", "what can")):
        return (
            "## 💡 What I can help with\n\n"
            "I can explain **flags**, **consent**, logging a diagnosis, **minor** vs **surrogate** roles, "
            "and general medical terms in plain language.\n\n"
            "I do not diagnose. Final judgment always stays with the doctor."
        )
    return (
        "## 💡 MEDREA\n\n"
        "I can explain how Hetu works and general medical terms in plain language. "
        "I could not reach the assistant service just now, so I cannot answer that specific question yet.\n\n"
        "Try again in a moment, or ask about **flags**, **access**, or **roles**."
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
        f"## 📋 Report received\n\n"
        f"I received a report from the **{role}** view for **{name}**.\n\n"
        f"- **On file:** {label_bit}\n"
        f"- **Flag status:** {flag_bit}\n\n"
        "This is a process summary only — I am not adding a diagnosis or choosing between doctors."
    )
