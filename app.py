
import streamlit as st
from utils.state import init_state
from utils.auth import check_auth
from utils.errors import friendly_error
from rag.chain import build_chain, get_retrieval_score
from router import route
from audio.stt import transcribe_audio
from audio.tts import speak

st.set_page_config(page_title="Family Assistant", layout="centered",
                   initial_sidebar_state="collapsed")

# Elderly CSS — big text, high contrast, big buttons
st.markdown("""
<style>
body, .stMarkdown, .stText { font-size: 22px !important; }
.stButton button {
    font-size: 24px !important;
    padding: 18px 30px !important;
    border-radius: 14px !important;
}
.stTextInput input { font-size: 20px !important; padding: 14px !important; }
.stTabs [data-baseweb="tab"] { font-size: 20px !important; }
</style>
""", unsafe_allow_html=True)

init_state()

if not check_auth():
    st.stop()

# ── lazy init chain ──────────────────────────────────────────
if st.session_state.rag_chain is None:
    with st.spinner("Starting up…"):
        chain, vs = build_chain("flash")
        st.session_state.rag_chain = chain
        st.session_state.vectorstore = vs
        st.session_state.current_model = "flash"

# ── error guard — blocks all UI if an error is pending ───────
if st.session_state.error_message:
    st.error(f"⚠️  {st.session_state.error_message}", icon="⚠️")
    if st.button("Try Again", use_container_width=True):
        st.session_state.error_message = None
        st.rerun()
    st.stop()

# ── main query handler ────────────────────────────────────────
def handle_query(query: str, has_image: bool = False):
    vs = st.session_state.vectorstore

    # Route
    score = get_retrieval_score(query, vs)
    decision = route(query, score, has_image)

    # Rebuild chain only if model changed
    if decision.model_key != st.session_state.current_model:
        chain, _ = build_chain(decision.model_key)
        st.session_state.rag_chain = chain
        st.session_state.current_model = decision.model_key

    chain = st.session_state.rag_chain

    # Immediate ack — kills the silence problem
    st.info(f"I heard: *{query}*")

    # Stream response into placeholder
    answer_box = st.empty()
    full_answer = ""
    try:
        for chunk in chain.stream({
            "question": query,
            "chat_history": st.session_state.conversation_history,
        }):
            token = chunk.get("answer", "")
            full_answer += token
            answer_box.markdown(f"### {full_answer}▌")
        answer_box.markdown(f"### {full_answer}")
    except Exception:
        st.session_state.error_message = friendly_error("model_timeout")
        st.rerun()

    st.session_state.conversation_history.append((query, full_answer))

    # TTS — non-fatal: failure doesn't break the app
    try:
        st.session_state.tts_audio = speak(full_answer)
    except Exception:
        pass


# ── UI ───────────────────────────────────────────────────────
st.title("👋 How can I help?")

tab_speak, tab_type, tab_photo = st.tabs(["🎤  Speak", "⌨️  Type", "📷  Photo"])

with tab_speak:
    audio = st.audio_input("Press and speak")
    if audio:
        with st.spinner("Listening…"):
            try:
                query = transcribe_audio(audio.read())
                handle_query(query)
            except NotImplementedError:
                st.warning("STT not yet wired in — use the Type tab for now.")
            except Exception:
                st.session_state.error_message = friendly_error("stt_failed")
                st.rerun()

with tab_type:
    query = st.text_input("Type your question:", placeholder="e.g. When do I take my blood pressure medicine?")
    if st.button("Ask", use_container_width=True, key="ask_btn") and query:
        handle_query(query)

with tab_photo:
    photo = st.camera_input("Take a photo") or st.file_uploader(
        "Or upload a photo", type=["jpg", "jpeg", "png"])
    if photo:
        # TODO: pass image bytes to vision model; for now treat as text query
        handle_query("I uploaded a photo. Please describe what you see.", has_image=True)

# ── TTS playback ─────────────────────────────────────────────
if st.session_state.tts_audio:
    st.audio(st.session_state.tts_audio, autoplay=True, format="audio/mp3")
    st.session_state.tts_audio = None   # prevent replay on next rerun
