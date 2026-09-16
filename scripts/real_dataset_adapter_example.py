"""
Example adapter: map an *authorized* clinical extract into HETU's contradiction schema.

This file contains NO real patient records. All values are placeholders.
Do not paste MIMIC, eICU, or n2c2 notes here. Obtain data only after
credentialing, DUA, and institutional approval.
"""

from __future__ import annotations

from typing import Any


HETU_ROOT_CAUSES = (
    "doctor_gap",
    "patient_gap",
    "no_fault",
    "intentional_non_disclosure",
)


def authorized_note_pair_to_hetu_fields(
    specialist_a_note: str | None,
    specialist_b_note: str | None,
    encounter_context: str | None,
) -> dict[str, Any]:
    """Return HETU input fields from already-authorized text.

    Replace the placeholder strings with fields from your approved extract
    (for example, two notes from different services plus a de-identified
    encounter summary). Do not invent access to restricted files.
    """
    specialist_a_finding = specialist_a_note or "<PLACEHOLDER specialist A finding>"
    specialist_b_finding = specialist_b_note or "<PLACEHOLDER specialist B finding>"
    patient_context = encounter_context or "<PLACEHOLDER de-identified context>"
    contradiction = (
        "<PLACEHOLDER: one-sentence description of how the two findings appear to conflict>"
    )
    return {
        "specialist_a_finding": specialist_a_finding,
        "specialist_b_finding": specialist_b_finding,
        "patient_context": patient_context,
        "contradiction": contradiction,
    }


def attach_model_output_placeholder(fields: dict[str, Any]) -> dict[str, Any]:
    """Show where a model would add labels. Not a clinical conclusion."""
    return {
        **fields,
        "root_cause": "<one of: " + ", ".join(HETU_ROOT_CAUSES) + ">",
        "reasoning": "<PLACEHOLDER cautious reasoning>",
        "appropriate_response": (
            "<PLACEHOLDER: blame-aware text; requires clinician review; "
            "do not state a definitive diagnosis>"
        ),
    }


def main() -> None:
    demo = authorized_note_pair_to_hetu_fields(None, None, None)
    labeled = attach_model_output_placeholder(demo)
    print("HETU schema keys:", sorted(labeled.keys()))
    print("Allowed root_cause values:", HETU_ROOT_CAUSES)
    print("Example placeholder object (fictional):")
    for key, value in labeled.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
