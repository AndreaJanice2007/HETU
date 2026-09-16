"""Test a fine-tuned HETU model on unseen contradiction cases.

Requires OPENAI_API_KEY and a fine-tuned model ID (FINE_TUNED_MODEL_ID or --model).
Never prints the API key.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from openai import OpenAI

ROOT_CAUSES = (
    "doctor_gap",
    "patient_gap",
    "no_fault",
    "intentional_non_disclosure",
)

SYSTEM_PROMPT = (
    "You are HETU, a clinical decision-support assistant. Analyze contradictions "
    "carefully, distinguish clinical evolution from genuine gaps, classify the root "
    "cause into exactly one of four categories, and provide a cautious, blame-aware "
    "response. Do not make definitive diagnoses."
)

# Held-out vignettes written for this script; they are not copied from training.jsonl.
UNSEEN_CASES = (
    {
        "id": "HETU_HOLD_001",
        "expected": "doctor_gap",
        "user": (
            "Specialist A finding: Nephrology progress note lists potassium as recently normal "
            "and continues a potassium-sparing diuretic.\n"
            "Specialist B finding: This morning's inpatient lab, already resulted in the same "
            "chart, shows potassium above the lab critical threshold.\n"
            "Patient context: The critical result was signed 90 minutes before the progress note.\n"
            "Contradiction: 'Recently normal' potassium versus a same-encounter critical high "
            "already in the chart."
        ),
    },
    {
        "id": "HETU_HOLD_002",
        "expected": "doctor_gap",
        "user": (
            "Specialist A finding: Pre-op note states no anticoagulation in the last seven days.\n"
            "Specialist B finding: Inpatient MAR in the same admission shows apixaban given "
            "yesterday evening.\n"
            "Patient context: The MAR entry is visible in the shared record used to write the "
            "pre-op note.\n"
            "Contradiction: No recent anticoagulation versus a documented dose the prior evening."
        ),
    },
    {
        "id": "HETU_HOLD_003",
        "expected": "patient_gap",
        "user": (
            "Specialist A finding: Rheumatology intake lists no over-the-counter pain medicines.\n"
            "Specialist B finding: Adult A later tells the pharmacist about daily high-dose "
            "ibuprofen bought at a corner shop, never entered on any med list.\n"
            "Patient context: The intake asked about 'prescriptions.' Adult A did not consider "
            "shop tablets to be medicines. Nothing in the chart predates this disclosure.\n"
            "Contradiction: No OTC pain medicines versus later report of daily high-dose ibuprofen."
        ),
    },
    {
        "id": "HETU_HOLD_004",
        "expected": "patient_gap",
        "user": (
            "Specialist A finding: Travel clinic documents no recent international travel.\n"
            "Specialist B finding: Adult A later recalls a two-week visit to a malaria-endemic "
            "region last month, remembered only after seeing a news clip, never previously documented.\n"
            "Patient context: No prior travel note exists in this fictional chart.\n"
            "Contradiction: No recent travel versus later recollection of a recent endemic-area trip."
        ),
    },
    {
        "id": "HETU_HOLD_005",
        "expected": "no_fault",
        "user": (
            "Specialist A finding: Day-0 blood culture: no growth at 24 hours.\n"
            "Specialist B finding: Day-2 update from the same bottles: Gram-positive cocci in clusters.\n"
            "Patient context: Serial microbiology from the same draw; the later result was not "
            "available when the first note was written.\n"
            "Contradiction: No growth at 24 hours versus later growth from the same culture set."
        ),
    },
    {
        "id": "HETU_HOLD_006",
        "expected": "no_fault",
        "user": (
            "Specialist A finding: Emergency radiograph: no definite fracture.\n"
            "Specialist B finding: Next-day orthopedic MRI: nondisplaced stress injury of the same bone.\n"
            "Patient context: Different modalities on sequential days; MRI was ordered because "
            "pain persisted after the radiograph.\n"
            "Contradiction: No fracture on radiograph versus later MRI describing a stress injury."
        ),
    },
    {
        "id": "HETU_HOLD_007",
        "expected": "intentional_non_disclosure",
        "user": (
            "Specialist A finding: Genetics internal note: a pathogenic variant is ready but will "
            "be discussed only in a scheduled pretest-completed counseling visit.\n"
            "Specialist B finding: Same-day patient portal message: 'genetic results are ready; "
            "counseling appointment booked' without naming the gene.\n"
            "Patient context: A documented counseling-before-gene-name policy is in the order comments.\n"
            "Contradiction: Internal named variant versus a portal note that does not name the gene."
        ),
    },
    {
        "id": "HETU_HOLD_008",
        "expected": "intentional_non_disclosure",
        "user": (
            "Specialist A finding: Adolescent medicine internal note: STI result pending a private "
            "in-person discussion per clinic confidentiality protocol.\n"
            "Specialist B finding: After-visit summary shared with the accompanying parent lists "
            "only 'follow-up lab discussion scheduled' and does not name the test.\n"
            "Patient context: The chart cites the clinic's adolescent confidentiality protocol "
            "and Adult A's documented preference for a private results visit.\n"
            "Contradiction: Internal pending STI result versus a parent-facing summary without the test name."
        ),
    },
)

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = REPO_ROOT / ".env"


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def require_api_key() -> None:
    load_dotenv(ENV_PATH)
    key = (
        os.environ.get("OPENAI_API_KEY", "").strip()
        or os.environ.get("MEDREA_API_KEY", "").strip()
    )
    if not key:
        print(
            "OPENAI_API_KEY is not set. Export it or add it to the gitignored .env file.",
            file=sys.stderr,
        )
        sys.exit(1)
    os.environ["OPENAI_API_KEY"] = key


def parse_assistant_json(text: str) -> dict | None:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:]
        stripped = stripped.strip()
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        default=os.environ.get("FINE_TUNED_MODEL_ID", ""),
        help="Fine-tuned model ID (or set FINE_TUNED_MODEL_ID)",
    )
    return parser.parse_args()


def main() -> int:
    load_dotenv(ENV_PATH)
    args = parse_args()
    require_api_key()

    model_id = (args.model or os.environ.get("FINE_TUNED_MODEL_ID", "")).strip()
    if not model_id:
        print(
            "Provide a fine-tuned model ID via --model or FINE_TUNED_MODEL_ID.",
            file=sys.stderr,
        )
        return 1

    client = OpenAI()
    correct = 0
    print("=" * 64)
    print("HETU unseen-case check")
    print(f"Model: {model_id}")
    print("=" * 64)

    for case in UNSEEN_CASES:
        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": case["user"]},
            ],
            temperature=0,
        )
        content = response.choices[0].message.content or ""
        payload = parse_assistant_json(content)
        predicted = payload.get("root_cause") if payload else None
        match = predicted == case["expected"]
        if match:
            correct += 1
        print(
            f"{case['id']}: expected={case['expected']} predicted={predicted} "
            f"{'OK' if match else 'MISMATCH'}"
        )
        if predicted not in ROOT_CAUSES:
            print("  warning: predicted label is not one of the four HETU categories")

    total = len(UNSEEN_CASES)
    print("=" * 64)
    print(f"Accuracy: {correct}/{total}")
    print("=" * 64)
    return 0 if correct == total else 1


if __name__ == "__main__":
    sys.exit(main())
