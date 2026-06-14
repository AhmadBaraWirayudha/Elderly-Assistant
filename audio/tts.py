"""
audio/tts.py — Text-to-speech via gTTS (offline-capable, no extra API key).

Upgrade path: swap gTTS for Google Cloud Text-to-Speech for higher-quality,
more natural voices and lower latency on longer responses.
"""

# audio/tts.py  — gTTS works offline; swap for provider TTS for better quality
from gtts import gTTS
import io
import config
from config import TTS_LANG
from __future__ import annotations
from providers.gemini_client import tts_to_wav_path

def speak(text: str, lang: str = config.TTS_LANG) -> bytes:
    """
    Convert text to MP3 audio bytes.

    Args:
        text: The answer text to speak aloud.
        lang: BCP-47 language code. Default from config (e.g. "en", "id").

    Returns:
        MP3 audio as raw bytes, ready for st.audio().
    """
    # Truncate very long answers for TTS to keep latency low.
    # Full text is still shown on screen.
     if len(text) > 500:
        spoken = text[:500].rsplit(" ", 1)[0] + "…"
    else:
        spoken = text
    tts = gTTS(text=spoken, lang=lang, text=text, lang=TTS_LANG, slow=False)
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    return buf.read()
    
def speak_to_wav(text: str, model_name: str) -> str:
    return tts_to_wav_path(model_name=model_name, text=text)
