# ─────────────────────────────────────────────────────────────
#  ElderAI — Configuration
#  Insert your Gemini API key below.  Everything else is tunable.
# ─────────────────────────────────────────────────────────────

# ── API ──────────────────────────────────────────────────────
GEMINI_API_KEY = "INSERT_YOUR_KEY_HERE"

# ── Models ───────────────────────────────────────────────────
GEMINI_MODELS = {
    "flash_lite": "gemini-2.5-flash-lite",   # fastest, cheapest
    "flash":      "gemini-2.5-flash",         # balanced default
    "reasoning":  "gemini-2.5-pro",           # hard questions
}

# ── Router thresholds ────────────────────────────────────────
ROUTER = {
    "score_high":        0.80,   # → flash_lite
    "score_medium":      0.55,   # → flash
    "words_short":       40,     # combined with score_high → flash_lite
    "words_medium":      80,     # above this → reasoning
}

# ── RAG ──────────────────────────────────────────────────────
KB_PATH      = "rag/kb/"
FAISS_PATH   = "kb_index"
CHUNK_SIZE   = 500
CHUNK_OVERLAP = 50
RETRIEVAL_K  = 3
RETRIEVAL_THRESHOLD = 0.40

# ── Memory ───────────────────────────────────────────────────
MAX_HISTORY  = 6      # conversation turns kept in context

# ── TTS ──────────────────────────────────────────────────────
TTS_LANG     = "en"   # change to "id" for Bahasa Indonesia

# ── Storage ──────────────────────────────────────────────────
HISTORY_DB   = "chat_history.db"

# ── Auth ─────────────────────────────────────────────────────
# Generate a new hash:  python -c "import hashlib; print(hashlib.sha256(b'your_pin').hexdigest())"
# Default PIN is 1234
PIN_HASH     = "03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4"

