"""
utils/validator.py — Input validation and sanitization.

Research report §3B / §3F:
  - Every request entering the model layer should have a strict schema.
  - Sanitize before persistence; guard against malformed payloads.
  - Safe handling of empty context.
"""
from __future__ import annotations

import re
import unicodedata

import config


# ── Constants ─────────────────────────────────────────────────────────────────
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]")


def sanitize_text(text: str) -> str:
    """
    Remove control characters, normalize unicode, collapse excess whitespace.
    Safe to call on any user-supplied string before passing to the model.
    """
    # Normalize unicode (NFC form)
    text = unicodedata.normalize("NFC", text)
    # Strip dangerous control characters (keep \t, \n, \r)
    text = _CONTROL_CHAR_RE.sub("", text)
    # Collapse runs of spaces (but not newlines)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def validate_query(raw: str) -> tuple[str, str | None]:
    """
    Validate and clean a text query.

    Returns:
        (cleaned_text, error_key | None)
        error_key is a key for utils.errors.friendly_error, or None if valid.
    """
    if not raw or not raw.strip():
        return "", "empty_query"

    cleaned = sanitize_text(raw)

    if not cleaned:
        return "", "empty_query"

    # Hard length limit — truncate silently to avoid model token overflow.
    if len(cleaned) > config.MAX_QUERY_CHARS:
        cleaned = cleaned[: config.MAX_QUERY_CHARS]

    return cleaned, None


def validate_image_bytes(data: bytes) -> tuple[bool, str | None]:
    """
    Basic sanity-check on uploaded image bytes.

    Returns:
        (ok, error_key | None)
    """
    if not data:
        return False, "image_unclear"
    # Minimum plausible size for a real image (a 1×1 PNG is ~67 bytes)
    if len(data) < 64:
        return False, "image_unclear"
    # Maximum 10 MB — Gemini's practical inline-data limit
    if len(data) > 10 * 1024 * 1024:
        return False, "image_too_large"
    return True, None
