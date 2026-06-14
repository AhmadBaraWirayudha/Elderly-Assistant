"""
utils/state.py — Single init function called at the top of every Streamlit rerun.

This is the only place default values are defined.  The pattern prevents
KeyError on first render and avoids duplicate conditionals across the app.
"""
from __future__ import annotations

import streamlit as st

# FIX: dict was named `DEFAULTS` but `init_state` referenced `_DEFAULTS` → NameError
# FIX: `"conversation_history"` key was duplicated (second entry silently overwrote first)
# FIX: `"tts_audio_path"` renamed to `"tts_audio"` to match app.py's usage
_DEFAULTS: dict = {
    "authenticated":          False,
    "conversation_history":   [],     # list of (query: str, answer: str)
    "messages":               [],
    "tts_audio":              None,   # bytes | None — cleared after each play
    "error_message":          None,   # str | None — rendered as error banner
    "rag_chain":              None,   # LangChain chain object
    "vectorstore":            None,   # FAISS vectorstore
    "current_model":          "flash",
    "last_query":             "",
    "last_ack":               "",
    "last_sources":           [],
    "show_history":           False,
    "knowledge_loaded":       False,
    "pending_input":          "",
}


def init_state() -> None:
    """Idempotent — safe to call on every script rerun."""
    for key, val in _DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = val
