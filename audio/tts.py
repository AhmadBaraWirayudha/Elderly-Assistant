"""
audio/tts.py — Text-to-speech via gTTS (no extra API key needed).

Upgrade path: swap gTTS for Google Cloud Text-to-Speech for higher-quality,
more natural voices and lower latency on longer responses.
"""
from __future__ import annotations   # FIX: moved to top (was after other imports → SyntaxError)

import io

from gtts import gTTS

import config

# FIX: removed `from providers.gemini_client import tts_to_wav_path` — unused
# FIX: removed duplicate `from config import TTS_LANG` — already covered by `import config`


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
    # The full text is still shown on screen.
    if len(text) > 500:               # FIX: had extra leading space → IndentationError
        spoken = text[:500].rsplit(" ", 1)[0] + "…"
    else:
        spoken = text

    # FIX: `gTTS(text=spoken, lang=lang, text=text, lang=TTS_LANG, slow=False)`
    #      had `text` and `lang` passed twice → TypeError: duplicate keyword argument
    tts = gTTS(text=spoken, lang=lang, slow=False)
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    return buf.read()

    # FIX: removed `speak_to_wav` that called providers with wrong signature
