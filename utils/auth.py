"""
utils/auth.py — Simple PIN gate.

Change the hash in .env (AUTH_PIN_HASH) to match your desired PIN:
  python -c "import hashlib; print(hashlib.sha256(b'YOUR_PIN').hexdigest())"
"""
from __future__ import annotations

import hashlib

import streamlit as st

import config

# FIX (from previous round): removed non-existent config imports.
# FIX (this round):          restored actual PIN verification — the check was
#                            removed, making any button press log in.


def check_auth() -> bool:
    """
    Returns True if the user is authenticated.
    Renders the PIN form and returns False otherwise.
    """
    if st.session_state.get("authenticated"):
        return True

    st.markdown(
        "<h1 style='text-align:center; font-size:2.5rem;'>👋 ElderAI</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center; font-size:1.3rem; color:#5f6368;'>"
        "Your personal AI assistant</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        pin = st.text_input(
            "Enter your PIN to continue:",
            type="password",
            key="_auth_pin",
            placeholder="e.g. 1234",
        )
        if st.button("✅  Enter", use_container_width=True, type="primary"):
            # FIX: actually check the PIN — was set to True unconditionally
            if hashlib.sha256(pin.encode()).hexdigest() == config.PIN_HASH:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Wrong PIN.  Please try again.", icon="🔒")

    return False
