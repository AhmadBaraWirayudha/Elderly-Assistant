"""
audio/stt.py — Speech-to-text via Gemini multimodal API.

Gemini Flash accepts audio files (WAV, MP3, etc.) and returns a transcript.
Upgrade path: swap for Google Cloud Speech-to-Text for lower-latency streaming.
"""
from __future__ import annotations   # FIX: moved to top (was after other imports → SyntaxError)

import os
import tempfile

import google.generativeai as genai

import config

# FIX: removed `from providers.gemini_client import transcribe_audio` —
#      it imported a function with the same name as the one defined below,
#      silently shadowing/conflicting with it.

_TRANSCRIBE_PROMPT = (
    "Transcribe the following audio exactly as spoken. "
    "Output only the transcription text, nothing else. "
    "If the audio is silent or unclear, output the single word: UNCLEAR"
)


def transcribe_audio(audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
    """
    Upload audio to Gemini Files API and return the transcript.

    Args:
        audio_bytes: Raw audio data from st.audio_input().read()
        mime_type:   MIME type of the audio (Streamlit records WAV by default)

    Returns:
        Transcription string, or raises RuntimeError on failure.
    """
    genai.configure(api_key=config.GEMINI_API_KEY)

    suffix = ".wav" if "wav" in mime_type else ".mp3"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name

    audio_file = None
    try:
        audio_file = genai.upload_file(path=tmp_path, mime_type=mime_type)
        model = genai.GenerativeModel(config.GEMINI_MODELS["flash"])
        response = model.generate_content([_TRANSCRIBE_PROMPT, audio_file])
        text = response.text.strip()

        if text.upper() == "UNCLEAR" or not text:
            raise RuntimeError("Audio was unclear or silent.")

        return text

    finally:
        os.unlink(tmp_path)
        if audio_file is not None:
            try:
                genai.delete_file(audio_file.name)
            except Exception:
                pass  # Non-fatal cleanup failure

    # FIX: removed unreachable `raise NotImplementedError` that was here
    # FIX: removed `transcribe_audio_bytes` that called transcribe_audio
    #      with a `model_name` kwarg the function doesn't accept
