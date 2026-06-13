from __future__ import annotations

from typing import List, Dict


def add_turn(history: list[dict], user_text: str, assistant_text: str) -> list[dict]:
    history.append({"role": "user", "content": user_text})
    history.append({"role": "assistant", "content": assistant_text})
    return history


def recent_messages(history: list[dict], limit: int = 10) -> list[dict]:
    if limit <= 0:
        return []
    return history[-limit:]


def history_as_prompt(history: list[dict], limit: int = 6) -> str:
    items = recent_messages(history, limit=limit * 2)
    lines: list[str] = []
    for msg in items:
        role = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)
