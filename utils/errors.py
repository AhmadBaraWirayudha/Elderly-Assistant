"""
utils/errors.py — Maps internal error types to calm, plain-language messages.

All messages follow one pattern:
  What happened (one sentence) + what to do next (one sentence).
"""
from __future__ import annotations

_MESSAGES: dict[str, str] = {
    "empty_query": (
        "I didn't catch a question. "
        "Please type or say what you would like to know."
    ),
    "stt_failed": (
        "I couldn't hear that clearly. "
        "Please press the microphone button and try speaking again."
    ),
    "image_unclear": (
        "The photo was hard for me to read. "
        "Try moving a little closer or finding better lighting."
    ),
    "image_too_large": (
        "That photo is too large to analyse. "
        "Try taking a closer, smaller photo instead."
    ),
    "retrieval_failed": (
        "I had trouble finding the right information. "
        "Try asking your question in a different way."
    ),
    "model_timeout": (
        "My thinking is taking too long right now. "
        "Please press Try Again in a moment."
    ),
    "no_api_key": (
        "The assistant is not set up yet. "
        "Please ask your family member to add the API key in the .env file."
    ),
    "generic": (
        "Something went wrong. "
        "Press the button below to try again."
    ),
}


def friendly_error(error_type: str) -> str:
    return _MESSAGES.get(error_type, _MESSAGES["generic"])
