"""
utils/history.py — SQLite persistence for conversation turns.

Research report improvements:
  §2C  explicit NOT NULL / CHECK / DEFAULT constraints on every column.
  §2D  index on ts for recency queries.
  §2F  schema_version migration table; forward-only versioned migrations
       with _add_col_if_missing guard against partial-crash re-runs.
  §2G  absolute path from config; WAL mode for concurrent reads.
  §3E  input_type, retrieval_score, latency_ms per turn for observability.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

import config
from utils.logger import log

_SCHEMA_VERSION = 2


class ChatTurn(NamedTuple):
    ts:               str
    query:            str
    answer:           str
    model_used:       str
    input_type:       str
    retrieval_score:  float | None
    latency_ms:       int | None


# ── Connection ────────────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    db_path = Path(config.HISTORY_DB)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ── Migration helpers ─────────────────────────────────────────────────────────

def _add_col_if_missing(
    conn: sqlite3.Connection,
    table: str,
    column: str,
    definition: str,
) -> None:
    """
    Add a column only when it does not already exist.

    SQLite has no ALTER TABLE … ADD COLUMN IF NOT EXISTS, so we inspect
    PRAGMA table_info first.  This makes every migration block safe to
    re-run after a partial-crash — a real scenario the v2 migration must
    survive.
    """
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        log.info("db_column_added", table=table, column=column)


def _get_schema_version(conn: sqlite3.Connection) -> int:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version  INTEGER PRIMARY KEY,
            applied  TEXT    NOT NULL
        )
    """)
    row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
    return row[0] or 0


def _apply_migrations(conn: sqlite3.Connection, current: int) -> None:
    if current < 1:
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
        conn.execute("INSERT OR IGNORE INTO schema_version VALUES (1, datetime('now'))")

    if current < 2:
        # Guarded with _add_col_if_missing so a mid-migration crash is safe
        _add_col_if_missing(conn, "chat_history", "input_type",
                            "TEXT NOT NULL DEFAULT 'text'")
        _add_col_if_missing(conn, "chat_history", "retrieval_score", "REAL")
        _add_col_if_missing(conn, "chat_history", "latency_ms",      "INTEGER")
        conn.execute("INSERT OR IGNORE INTO schema_version VALUES (2, datetime('now'))")


# ── Public API ────────────────────────────────────────────────────────────────

def init_db() -> None:
    """Create or migrate the schema.  Safe to call on every app startup."""
    with _conn() as conn:
        current = _get_schema_version(conn)
        if current < _SCHEMA_VERSION:
            log.info("db_migration_start", from_version=current,
                     to_version=_SCHEMA_VERSION)
            _apply_migrations(conn, current)
            conn.commit()
            log.info("db_migration_complete", version=_SCHEMA_VERSION)


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
                query, answer, model_used,
                input_type, retrieval_score, latency_ms,
            ),
        )
        conn.commit()


def get_recent(limit: int = 10) -> list[ChatTurn]:
    init_db()
    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT ts, query, answer, model_used,
                   input_type, retrieval_score, latency_ms
            FROM   chat_history
            ORDER  BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [ChatTurn(*r) for r in rows]


def get_stats() -> dict:
    init_db()
    with _conn() as conn:
        total   = conn.execute("SELECT COUNT(*) FROM chat_history").fetchone()[0]
        avg_lat = conn.execute(
            "SELECT AVG(latency_ms) FROM chat_history WHERE latency_ms IS NOT NULL"
        ).fetchone()[0]
        by_type = dict(conn.execute(
            "SELECT input_type, COUNT(*) FROM chat_history GROUP BY input_type"
        ).fetchall())
    return {
        "total_turns":    total,
        "avg_latency_ms": round(avg_lat or 0),
        "by_input_type":  by_type,
    }


def clear_history() -> None:
    init_db()
    with _conn() as conn:
        conn.execute("DELETE FROM chat_history")
        conn.commit()
