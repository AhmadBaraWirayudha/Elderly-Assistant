
# audio/tts.py  — gTTS works offline; swap for provider TTS for better quality
from gtts import gTTS
import io
from config import TTS_LANG
from __future__ import annotations
from providers.gemini_client import tts_to_wav_path

def speak(text: str) -> bytes:
    tts = gTTS(text=text, lang=TTS_LANG, slow=False)
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    return buf.read()
    
def speak_to_wav(text: str, model_name: str) -> str:
    return tts_to_wav_path(model_name=model_name, text=text)
