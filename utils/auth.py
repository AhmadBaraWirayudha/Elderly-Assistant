from __future__ import annotations
import hashlib
import streamlit as st
from config import ACCESS_PIN_HASH, PIN_ENABLED, APP_TITLE
from utils.errors import friendly_error

# Generate: hashlib.sha256(b"your_pin").hexdigest()
def _hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode("utf-8")).hexdigest()  # change before use

def check_auth() -> bool:
    if not PIN_ENABLED:
        st.session_state.authenticated = True
        return True
        
    if st.session_state.get("authenticated"):
        return True

    st.title(APP_TITLE)
    st.subheader("Protected access")
    pin = st.text_input("Enter your PIN:", type="password", key="_pin")
    entered = st.button("Enter", use_container_width=True)
    if entered:
        if pin and _hash_pin(pin) == ACCESS_PIN_HASH:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error(friendly_error("auth_failed"))
    return False

