from __future__ import annotations

import base64
import io
import os
import tempfile
import wave
from dataclasses import dataclass
from typing import Iterable, Optional

from google import genai
from google.genai import types
from PIL import Image

from config import GEMINI_API_KEY, GEMINI_MODELS


SYSTEM_SIMPLE = (
    "You are a calm, helpful assistant for elderly users and kindergarten children. "
    "Use short sentences, one idea at a time, and plain language. "
    "Avoid jargon. Ask at most one follow-up question."
)

SYSTEM_KID = (
    "You are a cheerful AI tutor for kindergarten children. "
    "Use very short sentences, simple words, and playful examples. "
    "Encourage learning through small games and one-question quizzes."
)

SYSTEM_ELDER = (
    "You are a helpful assistant for elderly users. "
    "Use large-step thinking, short answers, and practical guidance. "
    "Prioritize clarity and trust."
)


@dataclass
class GeminiResult:
    text: str
    raw: object | None = None


def client() -> genai.Client:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set.")
    return genai.Client(api_key=GEMINI_API_KEY)


def _voice_config():
    return types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Kore")
        )
    )


def _mime_from_name(name: str | None, default: str) -> str:
    if not name:
        return default
    lower = name.lower()
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".jpg") or lower.endswith(".jpeg"):
        return "image/jpeg"
    if lower.endswith(".webp"):
        return "image/webp"
    if lower.endswith(".wav"):
        return "audio/wav"
    if lower.endswith(".mp3"):
        return "audio/mpeg"
    if lower.endswith(".m4a"):
        return "audio/mp4"
    if lower.endswith(".webm"):
        return "audio/webm"
    return default


def _system_prompt(mode: str) -> str:
    mode = (mode or "").lower()
    if mode == "kid":
        return SYSTEM_KID
    if mode == "elderly":
        return SYSTEM_ELDER
    return SYSTEM_SIMPLE


def _build_text_prompt(user_query: str, context: str, history: str, mode: str, style_hint: str = "") -> str:
    system = _system_prompt(mode)
    parts = [system]
    if style_hint:
        parts.append(style_hint)
    if history:
        parts.append("Conversation history:\n" + history)
    if context:
        parts.append("Retrieved knowledge base context:\n" + context)
    parts.append("User question:\n" + user_query)
    parts.append(
        "Answer rules: be concise, truthful, and helpful. "
        "If context is missing, say so simply. "
        "For kids, use tiny examples. For elderly users, keep it practical."
    )
    return "\n\n".join(parts)


def stream_text(model_name: str, prompt: str) -> Iterable[str]:
    c = client()
    stream = c.models.generate_content_stream(
        model=model_name,
        contents=prompt,
    )
    for chunk in stream:
        piece = getattr(chunk, "text", "") or ""
        if piece:
            yield piece


def generate_text(model_name: str, prompt: str) -> str:
    c = client()
    response = c.models.generate_content(
        model=model_name,
        contents=prompt,
    )
    return getattr(response, "text", "") or ""


def answer_with_context(
    *,
    model_name: str,
    user_query: str,
    context: str,
    history: str,
    mode: str,
    style_hint: str = "",
) -> str:
    prompt = _build_text_prompt(
        user_query=user_query,
        context=context,
        history=history,
        mode=mode,
        style_hint=style_hint,
    )
    return generate_text(model_name, prompt)


def stream_answer_with_context(
    *,
    model_name: str,
    user_query: str,
    context: str,
    history: str,
    mode: str,
    style_hint: str = "",
) -> Iterable[str]:
    prompt = _build_text_prompt(
        user_query=user_query,
        context=context,
        history=history,
        mode=mode,
        style_hint=style_hint,
    )
    return stream_text(model_name, prompt)


def describe_image(*, model_name: str, image_bytes: bytes, mime_type: str, user_query: str, mode: str) -> str:
    c = client()
    prompt = _build_text_prompt(
        user_query=user_query,
        context="",
        history="",
        mode=mode,
        style_hint="Analyze the image first. Be careful and concrete.",
    )
    response = c.models.generate_content(
        model=model_name,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            prompt,
        ],
    )
    return getattr(response, "text", "") or ""


def transcribe_audio(*, model_name: str, audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
    c = client()
    prompt = (
        "Transcribe the audio into plain text. "
        "If it is unclear, provide the best possible transcription. "
        "Do not summarize."
    )
    response = c.models.generate_content(
        model=model_name,
        contents=[
            types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
            prompt,
        ],
    )
    return getattr(response, "text", "") or ""


def tts_to_wav_path(*, model_name: str, text: str) -> str:
    c = client()
    response = c.models.generate_content(
        model=model_name,
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=_voice_config(),
        ),
    )
    pcm = response.candidates[0].content.parts[0].inline_data.data

    fd, out_path = tempfile.mkstemp(suffix=".wav", prefix="family_ai_tts_")
    os.close(fd)
    with wave.open(out_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(pcm)
    return out_path


def build_kid_style_hint() -> str:
    return (
        "Make the answer playful, short, and interactive. "
        "Add one tiny question or game. "
        "Use a friendly mascot-like tone."
    )


def build_elder_style_hint() -> str:
    return (
        "Make the answer practical, calm, and easy to read. "
        "Prefer steps, not long paragraphs."
    )
