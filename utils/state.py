from __future__ import annotations
import streamlit as st

DEFAULTS = {
    "authenticated": False,
    "mode": "elderly",
    "messages": [],
    "conversation_history": [],
    "tts_audio_path": None,
    "error_message": None,
    "current_model": None,
    "vectorstore": None,
    "last_ack": "",
    "last_sources": [],
    "knowledge_loaded": False,
    "pending_input": "",
}

def init_state() -> None:
    for key, val in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = val
