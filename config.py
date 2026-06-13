
# All tunables in one place. Insert your key here.
GEMINI_API_KEY = "INSERT_YOUR_KEY_HERE"

GEMINI_MODELS = {
    "flash_lite": "gemini-2.5-flash-lite",
    "flash":      "gemini-2.5-flash",
    "reasoning":  "gemini-2.5-pro",
}

ROUTER = {
    "score_high":        0.80,   # → flash_lite
    "score_medium":      0.55,   # → flash
    "words_short":       40,     # short enough for flash_lite
    "words_medium":      80,     # medium → flash, above → reasoning
}

TTS_LANG     = "en"
KB_PATH      = "rag/kb/"
FAISS_PATH   = "kb_index"
HISTORY_DB   = "chat_history.db"
MAX_HISTORY  = 5                 # turns kept in memory
