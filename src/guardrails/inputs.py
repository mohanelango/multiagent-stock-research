from __future__ import annotations
import os
import re
from dataclasses import dataclass

_TICKER_RE = re.compile(r"^[A-Z0-9.\-]{1,10}$")  # allow BRK.B, RDS-A, etc.

@dataclass(frozen=True)
class ValidatedRequest:
    symbol: str
    days: int
    outdir: str


def sanitize_symbol(symbol: str) -> str:
    if symbol is None:
        raise ValueError("symbol is required")
    s = str(symbol).strip().upper()
    s = s.replace("/", ".")  # defensive normalization
    if not _TICKER_RE.match(s):
        raise ValueError(
            "Invalid symbol format. Allowed: 1-10 chars [A-Z0-9.-] (examples: AAPL, BRK.B)."
        )
    return s


def sanitize_days(days: int, *, min_days: int = 1, max_days: int = 10) -> int:
    try:
        d = int(days)
    except Exception:
        raise ValueError("days must be an integer")

    if d < min_days or d > max_days:
        raise ValueError(f"days out of range ({min_days}-{max_days})")
    return d


def sanitize_outdir(outdir: str) -> str:
    if outdir is None:
        raise ValueError("outdir is required")
    base = os.path.abspath(str(outdir).strip())
    # Prevent weird characters and accidental root writes
    if any(c in base for c in ["\0", "\n", "\r"]):
        raise ValueError("outdir contains invalid characters")
    return base


def validate_request(symbol: str, days: int, outdir: str) -> ValidatedRequest:
    return ValidatedRequest(
        symbol=sanitize_symbol(symbol),
        days=sanitize_days(days),
        outdir=sanitize_outdir(outdir),
    )
