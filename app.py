"""
app.py — ElderAI: Simplest AI Dashboard for Elderly Users
Maju Bareng AI 2025 · Hacktiv8 × Google

Entry point.  Run with:  streamlit run app.py
"""

from datetime import datetime
import google.generativeai as genai
from PIL import Image
import io

import config
from rag.chain import build_chain, get_retrieval_score, to_lcel_history
import streamlit as st
from utils.state import init_state
from utils.auth import check_auth
from utils.errors import friendly_error
from router import route
from audio.stt import transcribe_audio
from audio.tts import speak
from utils import history as db

# ── Page config (must be first Streamlit call) ────────────────────────────────

st.set_page_config(
    page_title="ElderAI",
    page_icon="👴",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# ── Elderly-first CSS ─────────────────────────────────────────────────────────

st.markdown("""
<style>
/* Base — large readable text */
html, body, [class*="css"] { font-size: 20px !important; }

/* Headings */
h1 { font-size: 2.2rem !important; font-weight: 700; }
h2 { font-size: 1.8rem !important; }
h3 { font-size: 1.5rem !important; }

/* Primary action buttons — big touch targets */
.stButton > button {
    font-size: 1.2rem !important;
    font-weight: 600 !important;
    padding: 16px 24px !important;
    border-radius: 12px !important;
    min-height: 58px !important;
    width: 100%;
}

/* Text input */
.stTextInput > label { font-size: 1.1rem !important; }
.stTextInput > div > div > input {
    font-size: 1.1rem !important;
    padding: 14px !important;
    border-radius: 10px !important;
}

/* Tabs — large and easy to tap */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}
.stTabs [data-baseweb="tab"] {
    font-size: 1.1rem !important;
    padding: 12px 20px !important;
    border-radius: 8px 8px 0 0 !important;
}

/* Alert / info boxes */
.stAlert { font-size: 1.1rem !important; border-radius: 10px; }

/* Answer area — the biggest text on screen */
.answer-card {
    background: #f8fbff;
    border-left: 6px solid #1a73e8;
    border-radius: 12px;
    padding: 20px 24px;
    margin-top: 12px;
    font-size: 1.3rem;
    line-height: 1.7;
    color: #202124;
}

/* Model badge */
.model-badge {
    display: inline-block;
    font-size: 0.75rem;
    background: #e8f0fe;
    color: #1a73e8;
    border-radius: 999px;
    padding: 2px 10px;
    margin-left: 8px;
    vertical-align: middle;
}

/* Divider spacing */
hr { margin: 24px 0 !important; }

/* Audio input label */
.stAudioInput > label { font-size: 1.1rem !important; }

/* Camera input label */
[data-testid="stCameraInput"] label { font-size: 1.1rem !important; }
</style>
""", unsafe_allow_html=True)

# ── Session & auth ────────────────────────────────────────────────────────────

init_state()

if not check_auth():
    st.stop()
  
# ── Validate API key ──────────────────────────────────────────────────────────

if config.GEMINI_API_KEY == "INSERT_YOUR_KEY_HERE":
    st.error(
        "⚙️  **Setup required:** Open `config.py` and replace "
        "`INSERT_YOUR_KEY_HERE` with your Gemini API key from "
        "[Google AI Studio](https://aistudio.google.com/).",
        icon="🔑",
    )
    st.stop()
  
# ── Lazy chain init ───────────────────────────────────────────────────────────

if st.session_state.rag_chain is None:
    with st.spinner("Starting ElderAI… this takes a few seconds the first time."):
        try:
            chain, vs = build_chain("flash")
            st.session_state.rag_chain = chain
            st.session_state.vectorstore = vs
            st.session_state.current_model = "flash"
        except Exception as exc:
            if "API_KEY" in str(exc).upper() or "invalid" in str(exc).lower():
                st.session_state.error_message = friendly_error("no_api_key")
            else:
                st.session_state.error_message = friendly_error("generic")

# ── Error guard — blocks UI until dismissed ───────────────────────────────────

if st.session_state.error_message:
    st.error(f"⚠️  {st.session_state.error_message}", icon="⚠️")
    if st.button("↩️  Try Again", use_container_width=True, type="primary"):
        st.session_state.error_message = None
        st.rerun()
    st.stop()


# ── Core query handler ────────────────────────────────────────────────────────

def handle_query(query: str, has_image: bool = False) -> None:
    """Route, stream answer, save, and generate TTS."""
    vs          = st.session_state.vectorstore
    chain       = st.session_state.rag_chain
    history     = st.session_state.conversation_history

    # ── Router ───────────────────────────────────────────────
    score    = get_retrieval_score(query, vs)
    decision = route(query, score, has_image)

    # Rebuild chain only when model changes
    if decision.model_key != st.session_state.current_model:
        with st.spinner(f"Switching to {decision.model_key}…"):
            chain, _ = build_chain(decision.model_key)
            st.session_state.rag_chain   = chain
            st.session_state.current_model = decision.model_key

    # ── Immediate acknowledgement — kills the silence ────────
    st.info(f"💬  I heard: *{query}*", icon="👂")

    # ── Stream response into the answer card ─────────────────
    answer_box   = st.empty()
    full_answer  = ""

    try:
        for chunk in chain.stream({
            "input":        query,
            "chat_history": to_lcel_history(history),
        }):
            token = chunk.get("answer", "")
            full_answer += token
            answer_box.markdown(
                f"<div class='answer-card'>{full_answer}▌</div>",
                unsafe_allow_html=True,
            )

        # Final render — remove cursor
        answer_box.markdown(
            f"<div class='answer-card'>{full_answer}</div>",
            unsafe_allow_html=True,
        )

    except Exception:
        st.session_state.error_message = friendly_error("model_timeout")
        st.rerun()
        return

    # ── Persist ───────────────────────────────────────────────
    st.session_state.conversation_history.append((query, full_answer))
    db.save_turn(query, full_answer, st.session_state.current_model)

    # ── TTS — non-fatal ───────────────────────────────────────
    try:
        st.session_state.tts_audio = speak(full_answer)
    except Exception:
        pass  # Voice unavailable; text answer is still shown


def handle_image_query(photo_file) -> None:
    """Send image directly to Gemini vision (bypasses RAG)."""
    genai.configure(api_key=config.GEMINI_API_KEY)

    try:
        image_bytes = photo_file.getvalue()
        img         = Image.open(io.BytesIO(image_bytes))
    except Exception:
        st.session_state.error_message = friendly_error("image_unclear")
        st.rerun()
        return

    prompt = (
        "You are a caring assistant helping an elderly person understand a photo.\n"
        "- If it shows a medicine or supplement label: read the medicine name, dosage, "
        "  and key instructions clearly. Do not give medical advice.\n"
        "- If it shows a document, bill, or letter: summarise the key information in "
        "  2-3 simple sentences.\n"
        "- If it shows an appliance or device: describe what you see and offer a simple tip.\n"
        "- For anything else: describe what is in the photo helpfully and simply.\n\n"
        "Always use short, plain language. Maximum 4 sentences."
    )

    st.info("📷  Analysing your photo…", icon="🔍")
    answer_box  = st.empty()
    full_answer = ""

    try:
        model    = genai.GenerativeModel(config.GEMINI_MODELS["flash"])
        response = model.generate_content([prompt, img])
        full_answer = response.text.strip()
    except Exception:
        st.session_state.error_message = friendly_error("image_unclear")
        st.rerun()
        return

    answer_box.markdown(
        f"<div class='answer-card'>{full_answer}</div>",
        unsafe_allow_html=True,
    )

    st.session_state.conversation_history.append(("(Photo)", full_answer))
    db.save_turn("(Photo)", full_answer, "flash-vision")

    try:
        st.session_state.tts_audio = speak(full_answer)
    except Exception:
        pass


# ── Header ────────────────────────────────────────────────────────────────────

col_title, col_info = st.columns([3, 1])
with col_title:
    st.markdown("## 👋 How can I help you?")
with col_info:
    model_label = st.session_state.current_model.replace("_", "-")
    now         = datetime.now().strftime("%H:%M")
    st.markdown(
        f"<p style='text-align:right; color:#5f6368; font-size:0.85rem;'>"
        f"🕐 {now}"
        f"<span class='model-badge'>{model_label}</span></p>",
        unsafe_allow_html=True,
    )

st.divider()

# ── Input tabs ────────────────────────────────────────────────────────────────

tab_speak, tab_type, tab_photo = st.tabs([
    "🎤  Speak",
    "⌨️  Type",
    "📷  Photo",
])

# ── Speak tab ─────────────────────────────────────────────────────────────────

with tab_speak:
    st.markdown("**Press the button and speak your question:**")
    audio = st.audio_input(" ", label_visibility="collapsed")

    if audio:
        with st.spinner("Listening to you…"):
            try:
                query = transcribe_audio(audio.read())
                handle_query(query)
            except RuntimeError:
                st.session_state.error_message = friendly_error("stt_failed")
                st.rerun()
            except Exception:
                st.session_state.error_message = friendly_error("stt_failed")
                st.rerun()

# ── Type tab ──────────────────────────────────────────────────────────────────

with tab_type:
    st.markdown("**Type your question below:**")
    query_text = st.text_input(
        " ",
        placeholder="e.g.  When do I take my blood pressure medicine?",
        label_visibility="collapsed",
        key="typed_query",
    )
    if st.button("✅  Ask", use_container_width=True, type="primary", key="ask_btn"):
        if query_text.strip():
            handle_query(query_text.strip())
        else:
            st.warning("Please type a question first.", icon="💬")

# ── Photo tab ─────────────────────────────────────────────────────────────────

with tab_photo:
    st.markdown("**Take a photo or upload one — I will explain it for you:**")

    photo_mode = st.radio(
        " ",
        ["📸  Take a Photo", "📁  Upload from Gallery"],
        horizontal=True,
        label_visibility="collapsed",
        key="photo_mode",
    )

    photo = None
    if "Take" in photo_mode:
        photo = st.camera_input(" ", label_visibility="collapsed")
    else:
        photo = st.file_uploader(
            " ",
            type=["jpg", "jpeg", "png", "webp"],
            label_visibility="collapsed",
        )

    if photo is not None:
        st.image(photo, caption="Your photo", use_container_width=True)
        if st.button("🔍  Analyse This Photo", use_container_width=True,
                     type="primary", key="analyse_btn"):
            handle_image_query(photo)

# ── TTS playback ──────────────────────────────────────────────────────────────

if st.session_state.tts_audio:
    st.markdown("---")
    st.markdown("🔊 **Listening to the answer:**")
    st.audio(st.session_state.tts_audio, format="audio/mp3", autoplay=True)
    st.session_state.tts_audio = None   # Clear after render to avoid replay

# ── Recent conversations ──────────────────────────────────────────────────────

st.divider()
with st.expander("📜  Recent Conversations", expanded=False):
    recent = db.get_recent(limit=5)
    if not recent:
        st.markdown("*No conversations yet. Ask me something!*")
    else:
        for ts, q, a, mdl in recent:
            st.markdown(f"**🕐 {ts}** — *model: {mdl}*")
            st.markdown(f"**You:** {q}")
            st.markdown(f"**Assistant:** {a}")
            st.divider()

    if recent and st.button("🗑️  Clear History", use_container_width=False,
                             key="clear_hist"):
        db.clear_history()
        st.session_state.conversation_history = []
        st.success("History cleared.")
        st.rerun()

# ── Footer ────────────────────────────────────────────────────────────────────

st.markdown(
    "<p style='text-align:center; color:#9aa0a6; font-size:0.8rem; margin-top:40px;'>"
    "ElderAI · Maju Bareng AI 2025 · Hacktiv8 × Google · Powered by Gemini 2.5"
    "</p>",
    unsafe_allow_html=True,
)
