"""Validate HETU training.jsonl for OpenAI chat supervised fine-tuning.

Read-only: never writes or modifies the dataset.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ALLOWED_ROLES = {"system", "user", "assistant"}
ROOT_CAUSES = (
    "doctor_gap",
    "patient_gap",
    "no_fault",
    "intentional_non_disclosure",
)
ASSISTANT_KEYS = {"root_cause", "reasoning", "appropriate_response"}
OPENAI_MIN_EXAMPLES = 10

# Names only are reported; matched substrings are never printed.
SECRET_PATTERNS = (
    ("openai_sk", re.compile(r"sk-[A-Za-z0-9_-]{10,}")),
    ("openai_sk_proj", re.compile(r"sk-proj-[A-Za-z0-9_-]{10,}")),
    ("openai_api_key_name", re.compile(r"OPENAI_API_KEY", re.IGNORECASE)),
    ("generic_api_key", re.compile(r"api[_-]?key\s*[:=]", re.IGNORECASE)),
    ("password_assignment", re.compile(r"password\s*[:=]", re.IGNORECASE)),
    ("bearer_token", re.compile(r"Bearer\s+[A-Za-z0-9._\-]+")),
    ("private_key_pem", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("github_token", re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}")),
    ("jwt", re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = REPO_ROOT / "training" / "training.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        nargs="?",
        default=str(DEFAULT_DATASET),
        help="Path to training.jsonl (default: repo training/training.jsonl)",
    )
    return parser.parse_args()


def load_lines(path: Path) -> list[tuple[int, str]]:
    text = path.read_text(encoding="utf-8")
    out: list[tuple[int, str]] = []
    for i, raw in enumerate(text.splitlines(), start=1):
        if raw.strip():
            out.append((i, raw))
    return out


def scan_secrets(line_no: int, text: str) -> list[str]:
    hits: list[str] = []
    for name, pattern in SECRET_PATTERNS:
        if pattern.search(text):
            hits.append(f"line {line_no}: {name}")
    return hits


def validate_example(line_no: int, obj: object) -> tuple[list[str], str | None, str | None]:
    errors: list[str] = []
    root_cause: str | None = None
    user_content: str | None = None

    if not isinstance(obj, dict):
        return ([f"line {line_no}: record is not a JSON object"], None, None)

    extra_top = sorted(set(obj.keys()) - {"messages"})
    if extra_top:
        errors.append(f"line {line_no}: unexpected top-level keys: {extra_top}")

    messages = obj.get("messages")
    if not isinstance(messages, list) or not messages:
        errors.append(f"line {line_no}: missing or empty 'messages' list")
        return (errors, None, None)

    roles: list[str] = []
    for j, msg in enumerate(messages):
        if not isinstance(msg, dict):
            errors.append(f"line {line_no}: messages[{j}] is not an object")
            continue
        extra_msg = sorted(set(msg.keys()) - {"role", "content"})
        if extra_msg:
            errors.append(f"line {line_no}: messages[{j}] unexpected keys: {extra_msg}")
        role = msg.get("role")
        content = msg.get("content")
        if role not in ALLOWED_ROLES:
            errors.append(f"line {line_no}: messages[{j}] invalid role {role!r}")
        else:
            roles.append(role)
        if not isinstance(content, str) or not content.strip():
            errors.append(f"line {line_no}: messages[{j}] content must be a non-empty string")
            continue
        if role == "user":
            user_content = content
        if role == "assistant":
            try:
                payload = json.loads(content)
            except json.JSONDecodeError as exc:
                errors.append(
                    f"line {line_no}: assistant content is not valid JSON ({exc.msg})"
                )
                continue
            if not isinstance(payload, dict):
                errors.append(f"line {line_no}: assistant JSON must be an object")
                continue
            missing = ASSISTANT_KEYS - set(payload.keys())
            extra = sorted(set(payload.keys()) - ASSISTANT_KEYS)
            if missing:
                errors.append(f"line {line_no}: assistant JSON missing keys: {sorted(missing)}")
            if extra:
                errors.append(f"line {line_no}: assistant JSON extra keys: {extra}")
            rc = payload.get("root_cause")
            if rc not in ROOT_CAUSES:
                errors.append(f"line {line_no}: invalid root_cause {rc!r}")
            else:
                root_cause = rc
            for field in ("reasoning", "appropriate_response"):
                value = payload.get(field)
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"line {line_no}: assistant '{field}' must be a non-empty string")

    if "user" not in roles:
        errors.append(f"line {line_no}: missing user message")
    if "assistant" not in roles:
        errors.append(f"line {line_no}: missing assistant message")

    return (errors, root_cause, user_content)


def main() -> int:
    args = parse_args()
    path = Path(args.path).resolve()
    errors: list[str] = []
    warnings: list[str] = []
    secret_hits: list[str] = []
    malformed: list[str] = []
    format_errors: list[str] = []
    categories: Counter[str] = Counter()
    fingerprints: defaultdict[str, list[int]] = defaultdict(list)
    user_prompts: defaultdict[str, list[int]] = defaultdict(list)
    valid_examples = 0

    print("=" * 64)
    print("HETU training.jsonl validation report")
    print("=" * 64)
    print(f"Path: {path}")

    if not path.is_file():
        print("1. File exists: FAIL")
        print("Dataset not found. No further checks.")
        return 1

    print("1. File exists: PASS")

    try:
        rows = load_lines(path)
    except OSError as exc:
        print(f"2. Valid JSONL: FAIL (could not read file: {exc})")
        return 1

    for line_no, raw in rows:
        secret_hits.extend(scan_secrets(line_no, raw))
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as exc:
            malformed.append(f"line {line_no}: {exc.msg} (col {exc.colno})")
            continue

        example_errors, root_cause, user_content = validate_example(line_no, obj)
        format_errors.extend(example_errors)
        if example_errors:
            continue

        valid_examples += 1
        if root_cause:
            categories[root_cause] += 1
        fingerprints[json.dumps(obj, sort_keys=True, ensure_ascii=False)].append(line_no)
        if user_content:
            user_prompts[user_content].append(line_no)

    jsonl_ok = not malformed
    print(f"2. Valid JSONL: {'PASS' if jsonl_ok else 'FAIL'}")
    print(f"   Non-empty lines: {len(rows)}")
    print(f"   json.loads failures: {len(malformed)}")

    chat_ok = not format_errors
    print(f"3. OpenAI chat fine-tuning format: {'PASS' if chat_ok else 'FAIL'}")
    print("   Required: messages[].role in {system, user, assistant}; non-empty content;")
    print("   at least one user and one assistant message per example.")

    print(f"4. Training examples: {valid_examples} valid / {len(rows)} non-empty lines")
    if valid_examples < OPENAI_MIN_EXAMPLES:
        warnings.append(
            f"OpenAI SFT requires at least {OPENAI_MIN_EXAMPLES} examples; found {valid_examples}."
        )

    unknown_categories = sorted(set(categories) - set(ROOT_CAUSES))
    missing_categories = [name for name in ROOT_CAUSES if categories[name] == 0]
    cat_ok = not unknown_categories
    print(f"5. HETU root-cause categories: {'PASS' if cat_ok else 'FAIL'}")
    print("6. Examples per category:")
    for name in ROOT_CAUSES:
        print(f"   {name}: {categories[name]}")
    other = sum(count for key, count in categories.items() if key not in ROOT_CAUSES)
    if other:
        print(f"   other/invalid: {other}")
    if missing_categories:
        warnings.append(f"No examples for: {', '.join(missing_categories)}")

    print(f"7. Malformed JSON: {'PASS' if jsonl_ok else 'FAIL'} ({len(malformed)} lines)")

    duplicate_records = {k: v for k, v in fingerprints.items() if len(v) > 1}
    duplicate_users = {k: v for k, v in user_prompts.items() if len(v) > 1}
    dup_ok = not duplicate_records and not duplicate_users
    print(f"8. Duplicate examples: {'PASS' if dup_ok else 'FAIL'}")
    print(f"   Duplicate full records: {len(duplicate_records)}")
    print(f"   Duplicate user prompts: {len(duplicate_users)}")

    secrets_ok = not secret_hits
    print(f"9. Secrets scan: {'PASS' if secrets_ok else 'FAIL'}")
    print(f"   Hits: {len(secret_hits)} (pattern names only; values not printed)")

    print("10. Dataset unmodified: PASS (this script is read-only)")

    errors.extend(malformed)
    errors.extend(format_errors)
    if unknown_categories:
        errors.append(f"unexpected root_cause values: {unknown_categories}")
    for lines in duplicate_records.values():
        errors.append(f"duplicate full example at lines {lines}")
    for lines in duplicate_users.values():
        errors.append(f"duplicate user prompt at lines {lines}")
    errors.extend(secret_hits)

    if warnings:
        print("-" * 64)
        print("Warnings:")
        for item in warnings:
            print(f"  - {item}")

    if errors:
        print("-" * 64)
        print("Issues:")
        for item in errors[:80]:
            print(f"  - {item}")
        if len(errors) > 80:
            print(f"  ... {len(errors) - 80} more")

    passed = jsonl_ok and chat_ok and cat_ok and dup_ok and secrets_ok and valid_examples > 0
    print("=" * 64)
    print(f"RESULT: {'PASS' if passed else 'FAIL'}")
    print("=" * 64)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
