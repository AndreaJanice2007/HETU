"""Diagnosis-label comparison helpers.

Live flagging uses OpenAI in logic.flag_detection. These local helpers remain
for seed data and as a last-resort display fallback.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

SIMILARITY_THRESHOLD = 0.85


def normalize_label(label: str) -> str:
    return re.sub(r"\s+", " ", (label or "").strip().lower())


def label_similarity(label_a: str, label_b: str) -> float:
    a, b = normalize_label(label_a), normalize_label(label_b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def labels_conflict(label_a: str, label_b: str) -> bool:
    return label_similarity(label_a, label_b) < SIMILARITY_THRESHOLD


def conflict_severity(label_a: str, label_b: str) -> str:
    sim = label_similarity(label_a, label_b)
    if sim < 0.2:
        return "critical"
    if sim < 0.35:
        return "high"
    if sim < 0.6:
        return "medium"
    return "low"
