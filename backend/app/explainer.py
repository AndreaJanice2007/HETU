"""Plain-language process explainer. Does not diagnose."""


def explain_process(
    *,
    viewer_is_minor: bool,
    patient_name: str,
    open_flag_count: int,
    resolved_flag_count: int,
    disclosed_diagnosis_count: int,
) -> dict:
    if viewer_is_minor:
        audience = (
            f"{patient_name}, this screen is view-only. "
            "Your surrogate handles corrections and access decisions."
        )
    else:
        audience = (
            f"This is a decision-support view for {patient_name}. "
            "Flags are suggestions, not verdicts — the doctor decides."
        )

    if open_flag_count:
        flags_text = (
            f"{open_flag_count} finding{'s' if open_flag_count != 1 else ''} "
            "from different doctors are waiting for clinical review. "
            "Diagnostic labels stay hidden until a doctor resolves the flag."
        )
    elif resolved_flag_count:
        flags_text = (
            f"{resolved_flag_count} earlier difference"
            f"{'' if resolved_flag_count == 1 else 's'} "
            f"{'has' if resolved_flag_count == 1 else 'have'} "
            "been reviewed. You can read the doctors' resolution notes below."
        )
    else:
        flags_text = "No open differences between doctors are on file right now."

    if disclosed_diagnosis_count:
        dx_text = (
            f"{disclosed_diagnosis_count} disclosed diagnosis record"
            f"{'s' if disclosed_diagnosis_count != 1 else ''} "
            "are visible. Hetu does not add its own diagnosis."
        )
    else:
        dx_text = "No diagnoses have been disclosed to this record yet."

    return {
        "title": "What Hetu is doing",
        "audience": audience,
        "flags": flags_text,
        "diagnoses": dx_text,
        "disclaimer": (
            "Hetu surfaces gaps between doctors. It does not confirm, rank, or "
            "treat any condition. Final judgment always stays with the doctor."
        ),
    }
