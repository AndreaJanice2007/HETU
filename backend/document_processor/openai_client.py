"""OpenAI client helpers. Never hard-code or print API keys."""

from __future__ import annotations

import os
from pathlib import Path

from openai import OpenAI

from document_processor.errors import OpenAIRequestError

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = REPO_ROOT / ".env"

# Official current multimodal model used in OpenAI vision examples:
# https://platform.openai.com/docs/guides/images-vision
# PDF file inputs are documented at:
# https://platform.openai.com/docs/guides/pdf-files
DEFAULT_VISION_MODEL = "gpt-6-astra"
# Official flagship model from https://platform.openai.com/docs/models
DEFAULT_MEDREA_MODEL = "gpt-6-astra"


def load_dotenv(path: Path = ENV_PATH) -> None:
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
    load_dotenv()
    key = (
        os.environ.get("OPENAI_API_KEY", "").strip()
        or os.environ.get("MEDREA_API_KEY", "").strip()
    )
    if not key:
        raise OpenAIRequestError(
            "OPENAI_API_KEY is not set. Export it or add it to the gitignored .env file."
        )
    os.environ["OPENAI_API_KEY"] = key
    return key


def vision_model() -> str:
    load_dotenv()
    return os.environ.get("HETU_VISION_MODEL", "").strip() or DEFAULT_VISION_MODEL


def medrea_model() -> str:
    load_dotenv()
    return os.environ.get("HETU_MEDREA_MODEL", "").strip() or DEFAULT_MEDREA_MODEL


def get_client() -> OpenAI:
    require_api_key()
    return OpenAI()
