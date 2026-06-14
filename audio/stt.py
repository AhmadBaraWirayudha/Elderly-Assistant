"""
audio/stt.py — Speech-to-text via Gemini multimodal API (new google-genai SDK).

Uses inline audio bytes (no file-upload round-trip) for lower latency.
Upgrade path: swap for Google Cloud Speech-to-Text for streaming transcription.
"""
from __future__ import annotations

from google import genai
from google.genai import types

import config
from utils.logger import log

_TRANSCRIBE_PROMPT = (
    "Transcribe the following audio exactly as spoken. "
    "Output only the transcription text, nothing else. "
    "If the audio is silent or unclear, output the single word: UNCLEAR"
)


def transcribe_audio(audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
    """
    Transcribe audio bytes using Gemini Flash (inline, no temp file).

    Args:
        audio_bytes: Raw audio from st.audio_input().read()
        mime_type:   Streamlit records WAV by default.

    Returns:
        Transcription string.

    Raises:
        RuntimeError: if audio is silent, unclear, or the API call fails.
    """
    client = genai.Client(api_key=config.GEMINI_API_KEY)

    response = client.models.generate_content(
        model=config.GEMINI_MODELS["flash"],
        contents=[
            types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
            _TRANSCRIBE_PROMPT,
        ],
    )

    text = (response.text or "").strip()
    log.info("stt_complete", chars=len(text))

    if text.upper() == "UNCLEAR" or not text:
        raise RuntimeError("Audio was unclear or silent.")

    return text
