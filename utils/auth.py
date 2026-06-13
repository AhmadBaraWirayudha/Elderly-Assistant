
import hashlib
import streamlit as st

# Generate: hashlib.sha256(b"your_pin").hexdigest()
PASSWORD_HASH = hashlib.sha256(b"1234").hexdigest()  # change before use

def check_auth() -> bool:
    if st.session_state.get("authenticated"):
        return True

    st.title("👋 Family Assistant")
    pin = st.text_input("Enter your PIN:", type="password", key="_pin")
    if st.button("Enter", use_container_width=True):
        if hashlib.sha256(pin.encode()).hexdigest() == PASSWORD_HASH:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Wrong PIN. Please try again.")
    return False
