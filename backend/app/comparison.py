"""Diagnosis-label comparison.

Swap the body of `labels_conflict` (or the similarity function) for Sentence-BERT
later. Callers should not import difflib or any embedding library directly.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

# Labels at or above this ratio are treated as the same finding (no flag).
SIMILARITY_THRESHOLD = 0.85


def normalize_label(label: str) -> str:
    return re.sub(r"\s+", " ", (label or "").strip().lower())


def label_similarity(label_a: str, label_b: str) -> float:
    """Return 0–1 similarity. Replace this function to use Sentence-BERT."""
    a, b = normalize_label(label_a), normalize_label(label_b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def labels_conflict(label_a: str, label_b: str) -> bool:
    """True when two doctors' labels should raise a reconciliation flag."""
    return label_similarity(label_a, label_b) < SIMILARITY_THRESHOLD


def conflict_severity(label_a: str, label_b: str) -> str:
    """Map label distance to a scanable severity band. Keep this next to similarity."""
    sim = label_similarity(label_a, label_b)
    if sim < 0.35:
        return "high"
    if sim < 0.6:
        return "medium"
    return "low"
