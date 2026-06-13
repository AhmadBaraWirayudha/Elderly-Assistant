from __future__ import annotations

from providers.gemini_client import transcribe_audio

# audio/stt.py  — swap in Whisper or Gemini STT later
def transcribe_audio(audio_bytes: bytes) -> str:
    raise NotImplementedError("Wire in Whisper or provider STT here")
def transcribe_audio_bytes(audio_bytes: bytes, model_name: str, mime_type: str = "audio/wav") -> str:
    return transcribe_audio(model_name=model_name, audio_bytes=audio_bytes, mime_type=mime_type)
