
# audio/tts.py  — gTTS works offline; swap for provider TTS for better quality
from gtts import gTTS
import io
from config import TTS_LANG

def speak(text: str) -> bytes:
    tts = gTTS(text=text, lang=TTS_LANG, slow=False)
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    return buf.read()
