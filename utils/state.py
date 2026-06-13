"""
utils/state.py — Single init function called at the top of every Streamlit rerun.

This is the only place default values are defined.  The pattern prevents
KeyError on first render and avoids duplicate conditionals across the app.
"""
from __future__ import annotations
import streamlit as st

DEFAULTS = {
    "authenticated": False,
    "conversation_history": [],     # list of (query: str, answer: str)
    
    "messages": [],
    "conversation_history": [],
    "tts_audio_path": None,          # bytes | None — cleared after each play
    "error_message": None,           # str | None — rendered as error banner
    "rag_chain": None,               # LangChain chain object
    "vectorstore": None,             # FAISS vectorstore
    "current_model": "flash",
    "last_query": "",
    "show_history": False,
    "last_ack": "",
    "last_sources": [],
    "knowledge_loaded": False,
    "pending_input": "",
}

def init_state() -> None:
    """Idempotent — safe to call on every script rerun."""
    for key, val in _DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = val
