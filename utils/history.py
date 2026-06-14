"""
utils/history.py — SQLite persistence for conversation turns.

Research report improvements applied:
  §2C  — explicit NOT NULL, CHECK, DEFAULT constraints on every column.
  §2D  — index on ts for recency queries.
  §2F  — schema_version migration table; forward-only versioned migrations.
  §2G  — absolute path resolved in config; WAL mode for safe concurrent reads.
  §3E  — store model observability metadata per turn (input_type, retrieval_score, latency_ms).
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

import config
from utils.logger import log


# ── Current schema version ────────────────────────────────────────────────────
_SCHEMA_VERSION = 2


# ── Return type for get_recent ────────────────────────────────────────────────
class ChatTurn(NamedTuple):
    ts:               str
    query:            str
    answer:           str
    model_used:       str
    input_type:       str
    retrieval_score:  float | None
    latency_ms:       int | None


# ── Connection helper ─────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    """
    Open a WAL-mode connection.  Path is absolute (from config) so it is
    immune to working-directory changes on Streamlit Cloud or Docker.
    """
    db_path = Path(config.HISTORY_DB)
    db_path.parent.mkdir(parents=True, exist_ok=True)   # Report §2G
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")              # safe concurrent reads
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ── Schema migrations ─────────────────────────────────────────────────────────

def _get_schema_version(conn: sqlite3.Connection) -> int:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version  INTEGER PRIMARY KEY,
            applied  TEXT NOT NULL
        )
    """)
    row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
    return row[0] or 0


def _apply_migrations(conn: sqlite3.Connection, current: int) -> None:
    """Forward-only migrations.  Each block is idempotent."""

    if current < 1:
        # v1: initial schema
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ts          TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
                query       TEXT    NOT NULL CHECK(length(query) > 0),
                answer      TEXT    NOT NULL,
                model_used  TEXT    NOT NULL DEFAULT 'flash'
                    CHECK(model_used IN ('lite','flash','pro','flash-vision','unknown'))
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_ts ON chat_history(ts)")
        conn.execute("INSERT INTO schema_version VALUES (1, datetime('now'))")

    if current < 2:
        # v2: observability columns (Report §3E)
        conn.execute("ALTER TABLE chat_history ADD COLUMN input_type      TEXT NOT NULL DEFAULT 'text'")
        conn.execute("ALTER TABLE chat_history ADD COLUMN retrieval_score REAL")
        conn.execute("ALTER TABLE chat_history ADD COLUMN latency_ms      INTEGER")
        conn.execute("INSERT INTO schema_version VALUES (2, datetime('now'))")


def init_db() -> None:
    """Create or migrate the database schema.  Safe to call on every startup."""
    with _conn() as conn:
        current = _get_schema_version(conn)
        if current < _SCHEMA_VERSION:
            log.info("db_migration_start", from_version=current, to_version=_SCHEMA_VERSION)
            _apply_migrations(conn, current)
            conn.commit()
            log.info("db_migration_complete", version=_SCHEMA_VERSION)


# ── Public API ────────────────────────────────────────────────────────────────

def save_turn(
    query: str,
    answer: str,
    model_used: str = "flash",
    *,
    input_type: str = "text",
    retrieval_score: float | None = None,
    latency_ms: int | None = None,
) -> None:
    init_db()
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO chat_history
                (ts, query, answer, model_used, input_type, retrieval_score, latency_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().isoformat(timespec="seconds"),
                query,
                answer,
                model_used,
                input_type,
                retrieval_score,
                latency_ms,
            ),
        )
        conn.commit()


def get_recent(limit: int = 10) -> list[ChatTurn]:
    """Return turns newest first."""
    init_db()
    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT ts, query, answer, model_used, input_type, retrieval_score, latency_ms
            FROM chat_history
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [ChatTurn(*r) for r in rows]


def get_stats() -> dict:
    """Return aggregate stats for the debug panel."""
    init_db()
    with _conn() as conn:
        total   = conn.execute("SELECT COUNT(*) FROM chat_history").fetchone()[0]
        avg_lat = conn.execute("SELECT AVG(latency_ms) FROM chat_history WHERE latency_ms IS NOT NULL").fetchone()[0]
        by_type = conn.execute(
            "SELECT input_type, COUNT(*) FROM chat_history GROUP BY input_type"
        ).fetchall()
    return {
        "total_turns":    total,
        "avg_latency_ms": round(avg_lat or 0),
        "by_input_type":  dict(by_type),
    }


def clear_history() -> None:
    init_db()
    with _conn() as conn:
        conn.execute("DELETE FROM chat_history")
        conn.commit()
