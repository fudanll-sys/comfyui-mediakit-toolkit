"""Small helpers for keeping credentials and signed URLs out of logs."""

from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit

_SECRET_PATTERNS = (
    re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,}\]]+"),
    re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)[^\s,}\]]+"),
    re.compile(r"(?i)(MEDIAKIT_API_KEY\s*[:=]\s*)[^\s]+"),
)


def strip_url_query(value: str) -> str:
    """Remove credentials commonly embedded in URL query strings."""
    try:
        parsed = urlsplit(value)
    except ValueError:
        return value
    if parsed.scheme not in {"http", "https"}:
        return value
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def redact_text(value: str) -> str:
    """Best-effort redaction for CLI diagnostics shown to users."""
    redacted = value
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub(r"\1<redacted>", redacted)
    redacted = re.sub(
        r"https?://[^\s\"'<>]+",
        lambda match: strip_url_query(match.group(0)),
        redacted,
    )
    return redacted

