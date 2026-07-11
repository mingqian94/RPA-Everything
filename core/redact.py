"""Redact common secrets and personal data before persisting local records."""

from __future__ import annotations

import re
from typing import Any

SENSITIVE_KEYS = {
    "api_key", "apikey", "authorization", "cookie", "cookies", "password", "passwd",
    "secret", "token", "access_token", "refresh_token", "session", "session_id",
}

_PATTERNS = (
    (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+"), r"\1<redacted>"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"), "<redacted-api-key>"),
    (re.compile(r"(?i)([?&](?:api[_-]?key|token|access_token|password|secret)=)[^&#\s]+"), r"\1<redacted>"),
    (re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"), "<redacted-phone>"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "<redacted-email>"),
)


def redact_text(value: str) -> str:
    """Return a display-safe form of text without attempting to parse its meaning."""
    for pattern, replacement in _PATTERNS:
        value = pattern.sub(replacement, value)
    return value


def redact(value: Any, key: str = "") -> Any:
    """Recursively redact values before they reach logs, traces, or run summaries."""
    if key.lower() in SENSITIVE_KEYS:
        return "<redacted>"
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {str(k): redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return [redact(item) for item in value]
    return value
