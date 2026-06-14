"""
config.py — ElderAI configuration.

API key and PIN are loaded from environment variables (or a .env file).
Never hard-code secrets here.  See .env.example for setup instructions.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file if present (ignored in production where real env vars are set)
load_dotenv()

# ── API key ───────────────────────────────────────────────────────────────────
# Set via GEMINI_API_KEY in .env or your host's environment.
GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "INSERT_YOUR_KEY_HERE")

# ── Auth PIN ──────────────────────────────────────────────────────────────────
# SHA-256 hash of the 4-digit PIN.  Default = 1234.
# Generate your own:  python -c "import hashlib; print(hashlib.sha256(b'YOUR_PIN').hexdigest())"
# Then set AUTH_PIN_HASH in .env or the environment.
PIN_HASH: str = os.environ.get(
    "AUTH_PIN_HASH",
    "03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4",
)

# ── Models ────────────────────────────────────────────────────────────────────
# Keys must stay in sync with router.py RouteDecision.model_key values.
GEMINI_MODELS: dict[str, str] = {
    "lite":  "gemini-2.5-flash-lite",   # fastest / cheapest
    "flash": "gemini-2.5-flash",         # balanced default
    "pro":   "gemini-2.5-pro",           # hard reasoning
}

# ── Router thresholds ─────────────────────────────────────────────────────────
ROUTER: dict[str, float | int] = {
    "score_high":   0.80,   # → lite
    "score_medium": 0.55,   # → flash
    "words_short":  40,     # combined with score_high → lite
    "words_medium": 80,     # above this → pro
}

# ── RAG ───────────────────────────────────────────────────────────────────────
KB_PATH             = "rag/kb/"
FAISS_PATH          = "kb_index"
CHUNK_SIZE          = 500
CHUNK_OVERLAP       = 50
RETRIEVAL_K         = 3
RETRIEVAL_THRESHOLD = 0.40

# ── Memory ────────────────────────────────────────────────────────────────────
MAX_HISTORY = 6      # conversation turns kept in LLM context

# ── TTS ───────────────────────────────────────────────────────────────────────
TTS_LANG = os.environ.get("TTS_LANG", "en")   # "id" for Bahasa Indonesia

# ── Storage (absolute path — prevents working-directory bugs) ─────────────────
# Report §2G: always resolve DB path to absolute at startup.
HISTORY_DB: str = str(Path(__file__).parent / "chat_history.db")

# ── Input limits ──────────────────────────────────────────────────────────────
MAX_QUERY_CHARS = 2_000   # truncated before reaching model
