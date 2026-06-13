
MESSAGES = {
    "stt_failed":       "I couldn't hear that clearly. Press the microphone button and try again.",
    "image_unclear":    "The photo is hard to read. Try moving closer or to better light.",
    "retrieval_failed": "I had trouble finding the right information. Try asking differently.",
    "model_timeout":    "My thinking is taking too long. Please try again in a moment.",
    "generic":          "Something went wrong. Press the button below to try again.",
}

def friendly_error(error_type: str) -> str:
    return MESSAGES.get(error_type, MESSAGES["generic"])
