from __future__ import annotations
import re
from typing import Iterable

# Block high-risk or disallowed phrasing for financial content
DEFAULT_FORBIDDEN = [
    "guaranteed returns",
    "cannot go down",
    "inside information",
    "sure shot",
    "risk free",
    "100% profit",
]

# Remove control chars that can break markdown/pdf rendering
_CTRL = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")

# Optional: strip extremely long repeated characters (prompt injection artifacts)
_REPEAT = re.compile(r"(.)\1{40,}")


def sanitize_text(text: str) -> str:
    if text is None:
        return ""
    t = str(text)
    t = _CTRL.sub("", t)
    t = _REPEAT.sub(r"\1" * 10, t)
    return t.strip()


def contains_forbidden(text: str, forbidden: Iterable[str]) -> bool:
    lower = text.lower()
    return any(term.lower() in lower for term in forbidden)


def enforce_neutrality(text: str, forbidden: Iterable[str] = DEFAULT_FORBIDDEN) -> str:
    """
    Final deterministic filter: sanitize + block forbidden claims.
    If forbidden found, we redact those phrases.
    """
    t = sanitize_text(text)
    for term in forbidden:
        # redact term in a case-insensitive way
        t = re.sub(re.escape(term), "[REDACTED]", t, flags=re.IGNORECASE)
    return t
