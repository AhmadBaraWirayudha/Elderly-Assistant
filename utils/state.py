
import streamlit as st

DEFAULTS = {
    "authenticated":          False,
    "conversation_history":   [],   # list of (query, answer) tuples
    "tts_audio":              None,
    "error_message":          None,
    "current_model":          "flash",
    "rag_chain":              None,
    "vectorstore":            None,
}

def init_state():
    for key, val in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = val
