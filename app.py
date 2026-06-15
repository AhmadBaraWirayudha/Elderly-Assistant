"""
app.py — ElderAI: Simplest AI Dashboard for Elderly Users
Maju Bareng AI 2025 · Hacktiv8 × Google

Entry point.  Run with:  streamlit run app.py
"""
from __future__ import annotations

import io
import time
from datetime import datetime
from pathlib import Path

import streamlit as st
from google import genai
from google.genai import types
from PIL import Image

import config
from rag.chain import (
    build_chain,
    get_retrieval_score,
    get_sources_from_chunks,
    to_lcel_history,
)
from router import route
from audio.stt import transcribe_audio
from audio.tts import speak
from utils import history as db
from utils.auth import check_auth
from utils.errors import friendly_error
from utils.health import run_checks
from utils.logger import log
from utils.state import init_state
from utils.validator import sanitize_text, validate_image_bytes, validate_query


# ── Streamlit Cloud secrets support ──────────────────────────────────────────
# On Streamlit Cloud, secrets live in st.secrets (set via the dashboard).
# Locally they live in .env (loaded by python-dotenv in config.py).
# This function reconciles both: st.secrets wins when present.

def _apply_streamlit_secrets() -> None:
    """Override config values from st.secrets if running on Streamlit Cloud."""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            config.GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
        if "AUTH_PIN_HASH" in st.secrets:
            config.PIN_HASH = st.secrets["AUTH_PIN_HASH"]
        if "TTS_LANG" in st.secrets:
            config.TTS_LANG = st.secrets["TTS_LANG"]
    except Exception:
        pass  # st.secrets unavailable in local dev — .env handles it


# ── Page config (must be the very first Streamlit call) ──────────────────────

st.set_page_config(
    page_title="ElderAI",
    page_icon="👴",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── CSS — elderly-first design ────────────────────────────────────────────────

st.markdown("""
<style>
html, body, [class*="css"] { font-size: 20px !important; }
h1  { font-size: 2.2rem !important; font-weight: 700; }
h2  { font-size: 1.8rem !important; }
h3  { font-size: 1.5rem !important; }
.stButton > button {
    font-size: 1.2rem !important; font-weight: 600 !important;
    padding: 16px 24px !important; border-radius: 12px !important;
    min-height: 58px !important; width: 100%;
}
.stTextInput > label { font-size: 1.1rem !important; }
.stTextInput > div > div > input {
    font-size: 1.1rem !important; padding: 14px !important;
    border-radius: 10px !important;
}
.stTabs [data-baseweb="tab-list"] { gap: 8px; }
.stTabs [data-baseweb="tab"] {
    font-size: 1.1rem !important; padding: 12px 20px !important;
    border-radius: 8px 8px 0 0 !important;
}
.stAlert { font-size: 1.1rem !important; border-radius: 10px; }
.answer-card {
    background: #f8fbff; border-left: 6px solid #1a73e8;
    border-radius: 12px; padding: 20px 24px; margin-top: 12px;
    font-size: 1.3rem; line-height: 1.7; color: #202124;
}
.model-badge {
    display: inline-block; font-size: 0.75rem; background: #e8f0fe;
    color: #1a73e8; border-radius: 999px; padding: 2px 10px; margin-left: 8px;
}
.warn-card {
    background: #fef9e7; border-left: 6px solid #f9a825; border-radius: 10px;
    padding: 14px 18px; margin-bottom: 12px; font-size: 1rem; color: #5d4037;
}
hr { margin: 24px 0 !important; }
</style>
""", unsafe_allow_html=True)

# ── Session & auth ────────────────────────────────────────────────────────────

init_state()
_apply_streamlit_secrets()  # must run before auth and API-key checks

if not check_auth():
    st.stop()

# ── Startup health checks (run once per session) ──────────────────────────────

if not st.session_state["_health_checked"]:
    st.session_state["_health_warnings"] = run_checks()
    st.session_state["_health_checked"]  = True

for w in st.session_state["_health_warnings"]:
    st.markdown(f"<div class='warn-card'>⚠️ {w}</div>", unsafe_allow_html=True)

# ── Hard stop on missing API key ──────────────────────────────────────────────

if config.GEMINI_API_KEY == "INSERT_YOUR_KEY_HERE":
    st.error(
        "⚙️ **Setup required:** Create a `.env` file and set `GEMINI_API_KEY`. "
        "Get your key at [Google AI Studio](https://aistudio.google.com/).",
        icon="🔑",
    )
    st.stop()

# ── Cached chain loader ───────────────────────────────────────────────────────
# @st.cache_resource: survives Streamlit reruns so the FAISS index
# is built once and reused — no spinner on every widget interaction.

@st.cache_resource(show_spinner=False)
def _load_chain(model_key: str):
    """Build and cache the RAG chain for a given model tier."""
    return build_chain(model_key)


def _ensure_chain(model_key: str = "flash") -> None:
    """Populate session_state with chain/vectorstore from the resource cache."""
    chain, vs = _load_chain(model_key)
    st.session_state.rag_chain    = chain
    st.session_state.vectorstore  = vs
    st.session_state.current_model = model_key


# Initialise on first render
if st.session_state.rag_chain is None:
    with st.spinner("Starting ElderAI — building knowledge index…"):
        try:
            _ensure_chain("flash")
        except Exception as exc:
            key = "no_api_key" if "API_KEY" in str(exc).upper() else "generic"
            st.session_state.error_message = friendly_error(key)
            log.error("chain_init_failed", exc=str(exc))

# ── Error guard ───────────────────────────────────────────────────────────────
# FIX: this block was commented out in the uploaded version.

if st.session_state.error_message:
    st.error(f"⚠️  {st.session_state.error_message}", icon="⚠️")
    if st.button("↩️  Try Again", use_container_width=True, type="primary"):
        st.session_state.error_message = None
        st.rerun()
    st.stop()


# ── Core handlers (research report §3: separated from UI layer) ───────────────

def _stream_answer(query: str, chain, history: list) -> tuple[str, list[str]]:
    """
    Stream the LLM answer into a Streamlit placeholder.

    Returns:
        (full_answer, sources_used)
    """
    answer_box   = st.empty()
    full_answer  = ""
    sources_used : list[str] = []

    for chunk in chain.stream({
        "input":        query,
        "chat_history": to_lcel_history(history),
    }):
        # Capture source documents from the first retrieval chunk
        if "context" in chunk and not sources_used:
            sources_used = get_sources_from_chunks(chunk["context"])

        token = chunk.get("answer", "")
        full_answer += token
        answer_box.markdown(
            f"<div class='answer-card'>{full_answer}▌</div>",
            unsafe_allow_html=True,
        )

    answer_box.markdown(
        f"<div class='answer-card'>{full_answer}</div>",
        unsafe_allow_html=True,
    )
    return full_answer, sources_used


def handle_query(
    query: str,
    has_image: bool = False,
    input_type: str = "text",
) -> None:
    """Validate → route → stream → persist → TTS."""

    clean, err = validate_query(query)
    if err:
        st.warning(friendly_error(err), icon="💬")
        return

    history = st.session_state.conversation_history
    vs      = st.session_state.vectorstore

    # ── Route ────────────────────────────────────────────────
    score    = get_retrieval_score(clean, vs)
    decision = route(clean, score, has_image)
    log.info("query_routed", input_type=input_type, score=round(score, 3),
             words=len(clean.split()), model=decision.model_key)

    if decision.model_key != st.session_state.current_model:
        with st.spinner(f"Switching to {decision.model_key}…"):
            _ensure_chain(decision.model_key)

    chain = st.session_state.rag_chain

    # ── Immediate ack — eliminates silent wait ────────────────
    st.info(f"💬  I heard: *{clean}*", icon="👂")

    # ── Stream ────────────────────────────────────────────────
    t0 = time.perf_counter()
    try:
        full_answer, sources = _stream_answer(clean, chain, history)
    except Exception as exc:
        log.error("stream_failed", exc=str(exc))
        st.session_state.error_message = friendly_error("model_timeout")
        st.rerun()
        return

    latency_ms = int((time.perf_counter() - t0) * 1000)

    # ── Source attribution ────────────────────────────────────
    if sources:
        st.caption(f"📚 From: {', '.join(sources)}")

    log.model("answer_complete", model=decision.model_key,
              latency_ms=latency_ms, retrieval_score=round(score, 3),
              answer_chars=len(full_answer), sources=sources)

    # ── Persist ───────────────────────────────────────────────
    st.session_state.conversation_history.append((clean, full_answer))
    db.save_turn(
        clean, full_answer, decision.model_key,
        input_type=input_type,
        retrieval_score=round(score, 3),
        latency_ms=latency_ms,
    )

    # ── TTS — non-fatal ───────────────────────────────────────
    try:
        st.session_state.tts_audio = speak(full_answer)
    except Exception as exc:
        log.warn("tts_failed", exc=str(exc))


def handle_image_query(photo_file) -> None:
    """Validate → Gemini vision → persist → TTS  (bypasses RAG)."""
    # FIX: removed debug client.models.list() loop that ran on every image

    try:
        image_bytes = photo_file.getvalue()
    except Exception:
        st.session_state.error_message = friendly_error("image_unclear")
        st.rerun()
        return

    ok, img_err = validate_image_bytes(image_bytes)
    if not ok:
        st.session_state.error_message = friendly_error(img_err or "image_unclear")
        st.rerun()
        return

    try:
        img = Image.open(io.BytesIO(image_bytes))
    except Exception:
        st.session_state.error_message = friendly_error("image_unclear")
        st.rerun()
        return

    prompt = (
        "You are a caring assistant helping an elderly person understand a photo.\n"
        "- Medicine label: read name, dosage, and key instructions clearly. No medical advice.\n"
        "- Document or letter: summarise key points in 2–3 simple sentences.\n"
        "- Appliance or device: describe what you see and offer a simple tip.\n"
        "- Anything else: describe the photo helpfully.\n"
        "Use short, plain language. Maximum 4 sentences."
    )

    st.info("📷  Analysing your photo…", icon="🔍")
    t0 = time.perf_counter()

    try:
        client   = genai.Client(api_key=config.GEMINI_API_KEY)
        response = client.models.generate_content(
            model=config.GEMINI_MODELS["flash"],
            contents=[prompt, img],
        )
        full_answer = (response.text or "").strip()
    except Exception as exc:
        log.error("vision_failed", exc=str(exc))
        st.session_state.error_message = friendly_error("image_unclear")
        st.rerun()
        return

    latency_ms = int((time.perf_counter() - t0) * 1000)
    log.model("image_answer_complete", model="flash-vision",
              latency_ms=latency_ms, answer_chars=len(full_answer))

    st.markdown(
        f"<div class='answer-card'>{full_answer}</div>",
        unsafe_allow_html=True,
    )

    st.session_state.conversation_history.append(("(Photo)", full_answer))
    db.save_turn("(Photo)", full_answer, "flash-vision",
                 input_type="image", latency_ms=latency_ms)

    try:
        st.session_state.tts_audio = speak(full_answer)
    except Exception as exc:
        log.warn("tts_failed", exc=str(exc))


# ── UI components (research report §4F: decomposed into functions) ────────────

def _render_header() -> None:
    col_title, col_info = st.columns([3, 1])
    with col_title:
        st.markdown("## 👋 How can I help you?")
    with col_info:
        now = datetime.now().strftime("%H:%M")
        mdl = st.session_state.current_model
        st.markdown(
            f"<p style='text-align:right; color:#5f6368; font-size:0.85rem;'>"
            f"🕐 {now}<span class='model-badge'>{mdl}</span></p>",
            unsafe_allow_html=True,
        )


def _render_speak_tab() -> None:
    st.markdown("**Press the button and speak your question:**")
    audio = st.audio_input(" ", label_visibility="collapsed")
    if audio:
        with st.spinner("Listening to you…"):
            try:
                query = transcribe_audio(audio.read())
                handle_query(query, input_type="voice")
            except RuntimeError:
                st.session_state.error_message = friendly_error("stt_failed")
                st.rerun()
            except Exception as exc:
                log.error("stt_unexpected", exc=str(exc))
                st.session_state.error_message = friendly_error("stt_failed")
                st.rerun()


def _render_type_tab() -> None:
    st.markdown("**Type your question below:**")
    query_text = st.text_input(
        " ",
        placeholder="e.g.  When do I take my blood pressure medicine?",
        label_visibility="collapsed",
        key="typed_query",
    )
    if st.button("✅  Ask", use_container_width=True, type="primary", key="ask_btn"):
        if query_text.strip():
            handle_query(query_text.strip(), input_type="text")
        else:
            st.warning(friendly_error("empty_query"), icon="💬")


def _render_photo_tab() -> None:
    st.markdown("**Take a photo or upload one — I will explain it for you:**")
    mode = st.radio(
        " ",
        ["📸  Take a Photo", "📁  Upload from Gallery"],
        horizontal=True,
        label_visibility="collapsed",
        key="photo_mode",
    )
    photo = (
        st.camera_input(" ", label_visibility="collapsed")
        if "Take" in mode
        else st.file_uploader(
            " ", type=["jpg", "jpeg", "png", "webp"],
            label_visibility="collapsed",
        )
    )
    if photo is not None:
        st.image(photo, caption="Your photo", use_container_width=True)
        if st.button("🔍  Analyse This Photo", use_container_width=True,
                     type="primary", key="analyse_btn"):
            handle_image_query(photo)


def _render_tts() -> None:
    if st.session_state.tts_audio:
        st.markdown("---")
        st.markdown("🔊 **Listening to the answer:**")
        st.audio(st.session_state.tts_audio, format="audio/mp3", autoplay=True)
        st.session_state.tts_audio = None


def _render_history_panel() -> None:
    with st.expander("📜  Recent Conversations", expanded=False):
        recent = db.get_recent(limit=5)
        if not recent:
            st.markdown("*No conversations yet. Ask me something!*")
        else:
            for turn in recent:
                lat  = f" · {turn.latency_ms} ms" if turn.latency_ms else ""
                score = f" · score {turn.retrieval_score:.2f}" if turn.retrieval_score else ""
                st.markdown(
                    f"**🕐 {turn.ts}** — *{turn.model_used} · {turn.input_type}{lat}{score}*"
                )
                st.markdown(f"**You:** {turn.query}")
                st.markdown(f"**Assistant:** {turn.answer}")
                st.divider()

        col_a, col_b = st.columns([1, 1])
        with col_a:
            if recent and st.button("🗑️  Clear History", use_container_width=True,
                                     key="clear_hist"):
                db.clear_history()
                st.session_state.conversation_history = []
                st.success("History cleared.")
                st.rerun()
        with col_b:
            stats = db.get_stats()
            st.caption(
                f"💬 {stats['total_turns']} turns  ·  "
                f"⚡ avg {stats['avg_latency_ms']} ms  ·  "
                + "  ".join(f"{k}: {v}" for k, v in stats["by_input_type"].items())
            )


# ── Main layout ───────────────────────────────────────────────────────────────

_render_header()
st.divider()

tab_speak, tab_type, tab_photo = st.tabs(["🎤  Speak", "⌨️  Type", "📷  Photo"])

with tab_speak:
    _render_speak_tab()

with tab_type:
    _render_type_tab()

with tab_photo:
    _render_photo_tab()

_render_tts()
st.divider()
_render_history_panel()

st.markdown(
    "<p style='text-align:center; color:#9aa0a6; font-size:0.8rem; margin-top:40px;'>"
    "ElderAI · Maju Bareng AI 2025 · Hacktiv8 × Google · Powered by Gemini 2.5"
    "</p>",
    unsafe_allow_html=True,
)
