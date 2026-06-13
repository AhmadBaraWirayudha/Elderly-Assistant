from __future__ import annotations
from typing import List, Dict
import sqlite3
from datetime import datetime
import config

def _conn() -> sqlite3.Connection:
    return sqlite3.connect(config.HISTORY_DB)

def init_db() -> None:
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ts          TEXT    NOT NULL,
                query       TEXT    NOT NULL,
                answer      TEXT    NOT NULL,
                model_used  TEXT    NOT NULL DEFAULT 'flash'
            )
        """)
        conn.commit()

def save_turn(query: str, answer: str, model_used: str = "flash") -> None:
    init_db()
    with _conn() as conn:
        conn.execute(
            "INSERT INTO chat_history (ts, query, answer, model_used) VALUES (?, ?, ?, ?)",
            (datetime.now().isoformat(timespec="seconds"), query, answer, model_used),
        )
        conn.commit()


def get_recent(limit: int = 10) -> list[tuple]:
    """Return [(ts, query, answer, model_used), ...] newest first."""
    init_db()
    with _conn() as conn:
        rows = conn.execute(
            "SELECT ts, query, answer, model_used FROM chat_history "
            "ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return rows


def clear_history() -> None:
    init_db()
    with _conn() as conn:
        conn.execute("DELETE FROM chat_history")
        conn.commit()
