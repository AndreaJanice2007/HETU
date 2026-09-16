"""External credential checks for guest judges.

Guest doctors have no Hetu credibility_score, so verification is based on
license format (demo) plus the fact that a registered doctor sent the invite.
"""

from __future__ import annotations

import re

# Letters/digits with optional separators, at least 6 meaningful characters.
LICENSE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9/.\-]{5,79}$")


def verify_license(license_number: str) -> bool:
    """Placeholder license check for the hackathon demo.

    In production this would call a real medical license registry API
    (e.g. National Medical Commission API for India, or NPI registry for US)
    and confirm the number is active and matches the named clinician.
    """
    value = (license_number or "").strip()
    if not value:
        return False
    return bool(LICENSE_PATTERN.match(value))
