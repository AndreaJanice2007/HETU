"""Shared OpenAI helpers. Never print or hard-code API keys.

Uses the same client and model path as Medrea (responses API).
"""

from __future__ import annotations

import json
import logging
import os
import re

from document_processor.errors import OpenAIRequestError
from document_processor.openai_client import get_client, load_dotenv, medrea_model

logger = logging.getLogger(__name__)

NO_CLINICAL_JUDGMENT = (
    "You must not diagnose the patient. You must not declare a doctor right or wrong. "
    "You must not compare treatment correctness or suggest clinical next steps."
)


def _model() -> str:
    load_dotenv()
    return os.environ.get("HETU_FLAG_MODEL", "").strip() or medrea_model()


def _output_text(response) -> str:
    return (getattr(response, "output_text", None) or "").strip()


def _parse_json(text: str) -> dict | None:
    cleaned = (text or "").strip()
    if not cleaned:
        return None
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        payload = json.loads(cleaned)
        return payload if isinstance(payload, dict) else None
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            payload = json.loads(cleaned[start : end + 1])
            return payload if isinstance(payload, dict) else None
        except json.JSONDecodeError:
            return None


def chat_text(prompt: str, *, temperature: float = 0) -> str | None:
    del temperature
    try:
        client = get_client()
        response = client.responses.create(model=_model(), input=prompt)
        return _output_text(response) or None
    except OpenAIRequestError as exc:
        logger.warning("OpenAI text call skipped: %s", exc.detail)
        return None
    except Exception as exc:
        logger.warning("OpenAI text call failed: %s", type(exc).__name__)
        return None


def chat_json(prompt: str, *, temperature: float = 0) -> dict | None:
    del temperature
    try:
        client = get_client()
        response = client.responses.create(model=_model(), input=prompt)
        return _parse_json(_output_text(response))
    except OpenAIRequestError as exc:
        logger.warning("OpenAI JSON call skipped: %s", exc.detail)
        return None
    except Exception as exc:
        logger.warning("OpenAI JSON call failed: %s", type(exc).__name__)
        return None
