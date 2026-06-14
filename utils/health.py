"""
utils/health.py — Startup health checks.

Research report §8 (debugging checklist):
  - Verify database path exists before connection.
  - Verify schema is created before first query.
  - Check startup order and import side effects.
  - Ops target: startup health check, DB connectivity check.

Call run_checks() once at app startup; display warnings if any issues found.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import config
from utils.logger import log


def run_checks() -> list[str]:
    """
    Run all startup checks.

    Returns a list of human-readable warning strings.
    Empty list means everything is fine.
    """
    warnings: list[str] = []

    # 1. API key
    _check_api_key(warnings)

    # 2. DB path and connectivity
    _check_database(warnings)

    # 3. KB directory
    _check_kb(warnings)

    # 4. FAISS cache coherence (non-fatal)
    _check_faiss(warnings)

    if warnings:
        for w in warnings:
            log.warn("startup_check_failed", issue=w)
    else:
        log.info("startup_checks_passed")

    return warnings


# ── Individual checks ─────────────────────────────────────────────────────────

def _check_api_key(warnings: list[str]) -> None:
    if config.GEMINI_API_KEY in ("INSERT_YOUR_KEY_HERE", "", None):
        warnings.append(
            "Gemini API key is not set. Open .env and set GEMINI_API_KEY."
        )


def _check_database(warnings: list[str]) -> None:
    db_path = Path(config.HISTORY_DB)
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        warnings.append(f"Cannot create DB directory '{db_path.parent}': {exc}")
        return

    try:
        conn = sqlite3.connect(str(db_path))
        conn.execute("SELECT 1")
        conn.close()
    except sqlite3.Error as exc:
        warnings.append(f"Database connection failed: {exc}")


def _check_kb(warnings: list[str]) -> None:
    kb = Path(config.KB_PATH)
    if not kb.exists():
        warnings.append(
            f"Knowledge base directory '{config.KB_PATH}' is missing. "
            "The assistant will answer from general knowledge only."
        )
    elif not any(kb.glob("**/*.txt")):
        warnings.append(
            f"Knowledge base '{config.KB_PATH}' has no .txt files. "
            "Add documents to personalise the assistant."
        )


def _check_faiss(warnings: list[str]) -> None:
    faiss_path = Path(config.FAISS_PATH)
    kb_path    = Path(config.KB_PATH)

    if faiss_path.exists() and kb_path.exists():
        kb_mtime    = max((f.stat().st_mtime for f in kb_path.glob("**/*.txt")), default=0)
        faiss_mtime = max((f.stat().st_mtime for f in faiss_path.iterdir()), default=0)
        if kb_mtime > faiss_mtime:
            warnings.append(
                "Knowledge base files are newer than the FAISS index. "
                f"Delete '{config.FAISS_PATH}/' and restart to rebuild the index."
            )
