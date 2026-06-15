"""
utils/state.py — Single init function called at the top of every Streamlit rerun.

All session_state keys with their defaults live here.
Avoids KeyError on first render and scattered st.session_state.get() calls everywhere.
"""
from __future__ import annotations

import uuid

import streamlit as st

_DEFAULTS: dict = {
    # ── Auth ──────────────────────────────────────────────────
    "authenticated":          False,

    # ── Conversation ──────────────────────────────────────────
    "conversation_history":   [],      # list of (query: str, answer: str)
    "session_id":             "",      # unique per browser session (set below)

    # ── Audio / TTS ───────────────────────────────────────────
    "tts_audio":              None,    # bytes | None — cleared after each play

    # ── UI state ──────────────────────────────────────────────
    "error_message":          None,    # str | None — renders error banner + stops UI
    "show_history":           False,

    # ── Chain / model ─────────────────────────────────────────
    "rag_chain":              None,    # cached via @st.cache_resource; ref stored here
    "vectorstore":            None,    # same
    "current_model":          "flash",

    # ── Health checks ─────────────────────────────────────────
    # FIX: these two keys were used in app.py but missing here → KeyError
    "_health_checked":        False,
    "_health_warnings":       [],
}


def init_state() -> None:
    """Idempotent — safe to call on every script rerun."""
    for key, val in _DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = val

    # session_id must be unique per browser tab, not shared across sessions.
    # Cannot use a static default in _DEFAULTS (uuid would be evaluated once at import).
    if not st.session_state.get("session_id"):
        st.session_state["session_id"] = uuid.uuid4().hex[:8]
