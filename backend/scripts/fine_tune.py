"""Upload training.jsonl and create an OpenAI supervised fine-tuning job.

Do not hard-code API keys. Loads OPENAI_API_KEY from the environment
(or from the repo .env file if the variable is unset). Never prints the key.

Default base model is taken from OpenAI's supervised fine-tuning docs:
https://platform.openai.com/docs/guides/supervised-fine-tuning
Currently supported SFT models listed there:
  - gpt-4.1-2025-04-14
  - gpt-4.1-mini-2025-04-14
  - gpt-4.1-nano-2025-04-14
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from openai import OpenAI

# Official SFT model IDs from platform.openai.com/docs/guides/supervised-fine-tuning
# (fetched 2026-09-15). Classification is listed as an SFT use case.
SUPPORTED_SFT_MODELS = (
    "gpt-4.1-2025-04-14",
    "gpt-4.1-mini-2025-04-14",
    "gpt-4.1-nano-2025-04-14",
)
DEFAULT_MODEL = "gpt-4.1-mini-2025-04-14"

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = REPO_ROOT / "training" / "training.jsonl"
ENV_PATH = REPO_ROOT / ".env"
TERMINAL_STATUSES = {"succeeded", "failed", "cancelled"}


def load_dotenv(path: Path) -> None:
    """Load KEY=VALUE pairs into os.environ without overwriting existing vars."""
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


def require_api_key() -> str:
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
    return key


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--training-file",
        default=str(DEFAULT_DATASET),
        help="Path to JSONL training data",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Base model ID (default: {DEFAULT_MODEL})",
    )
    parser.add_argument("--suffix", default="hetu-sft", help="Optional fine-tuned model suffix")
    parser.add_argument("--poll-interval", type=int, default=20, help="Seconds between status polls")
    parser.add_argument("--no-poll", action="store_true", help="Create the job and exit without polling")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    require_api_key()

    if args.model not in SUPPORTED_SFT_MODELS:
        print(
            f"Model {args.model!r} is not in the official SFT list from "
            "https://platform.openai.com/docs/guides/supervised-fine-tuning : "
            f"{', '.join(SUPPORTED_SFT_MODELS)}",
            file=sys.stderr,
        )
        return 1

    training_path = Path(args.training_file).resolve()
    if not training_path.is_file():
        print(f"Training file not found: {training_path}", file=sys.stderr)
        return 1

    client = OpenAI()  # uses OPENAI_API_KEY from the environment; key is not printed

    print(f"Uploading {training_path.name} (purpose=fine-tune)...")
    with training_path.open("rb") as handle:
        uploaded = client.files.create(file=handle, purpose="fine-tune")
    print(f"Uploaded file ID: {uploaded.id}")

    print(f"Creating supervised fine-tuning job on {args.model}...")
    job = client.fine_tuning.jobs.create(
        training_file=uploaded.id,
        model=args.model,
        suffix=args.suffix,
        method={"type": "supervised"},
    )
    print(f"Fine-tuning job ID: {job.id}")
    print(f"Status: {job.status}")

    if args.no_poll:
        print("Polling skipped (--no-poll). Check the job later with the printed job ID.")
        return 0

    while job.status not in TERMINAL_STATUSES:
        time.sleep(max(args.poll_interval, 1))
        job = client.fine_tuning.jobs.retrieve(job.id)
        print(f"Status: {job.status}")

    if job.status != "succeeded":
        error = getattr(job, "error", None)
        print(f"Fine-tuning did not succeed (status={job.status}).", file=sys.stderr)
        if error:
            print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"Fine-tuned model ID: {job.fine_tuned_model}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
