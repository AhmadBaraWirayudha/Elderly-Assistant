"""
utils/logger.py — Structured logging for ElderAI.

Research report §5B: use structured logs with consistent keys.
Every log entry is a single JSON line.  Grep-friendly and APM-ready.

Usage:
    from utils.logger import log
    log.info("query_received", input_type="text", length=42)
    log.error("stt_failed", reason="timeout")
    log.model("answer_complete", model="flash", latency_ms=820, retrieval_score=0.77)
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

# One root handler: stdout so Streamlit Cloud / Docker captures it.
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(message)s"))

_root = logging.getLogger("elderai")
_root.setLevel(logging.DEBUG)
if not _root.handlers:
    _root.addHandler(_handler)


class _StructuredLogger:
    """Thin wrapper that emits JSON lines with a fixed set of base keys."""

    def __init__(self, name: str) -> None:
        self._log = logging.getLogger(name)

    def _emit(self, level: str, event: str, **kwargs: Any) -> None:
        record = {
            "ts":    datetime.now(tz=timezone.utc).isoformat(timespec="milliseconds"),
            "level": level,
            "event": event,
            **kwargs,
        }
        self._log.info(json.dumps(record, default=str))

    def info(self, event: str, **kwargs: Any) -> None:
        self._emit("INFO", event, **kwargs)

    def warn(self, event: str, **kwargs: Any) -> None:
        self._emit("WARN", event, **kwargs)

    def error(self, event: str, **kwargs: Any) -> None:
        self._emit("ERROR", event, **kwargs)

    def model(self, event: str, **kwargs: Any) -> None:
        """Convenience for model-run observability lines."""
        self._emit("MODEL", event, **kwargs)


# Module-level singleton — import this everywhere.
log = _StructuredLogger("elderai")
