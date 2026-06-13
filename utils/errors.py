from __future__ import annotations
"""
utils/errors.py — Maps internal error types to plain, calm messages.

All messages follow the same pattern:
  What happened (one sentence) + what to do next (one sentence).
"""

_MESSAGES: dict[str, str] = {
    "stt_failed": (
        "I couldn't hear that clearly. "
        "Please press the microphone button and try speaking again."
    ),
    "image_unclear": (
        "The photo was hard for me to read. "
        "Try moving a little closer or finding better lighting."
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
        "Please ask your family member to add the API key in config.py."
    ),
    "generic": (
        "Something went wrong. "
        "Press the button below to try again."
    ),
}

def friendly_error(error_type: str) -> str:
    return _MESSAGES.get(error_type, _MESSAGES["generic"])
