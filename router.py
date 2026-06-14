"""
router.py — Decides which Gemini model tier to use for a given query.

Decision tree:
  Image present                              →  flash
  score >= score_high  AND  words <= short   →  lite   (fast, cheap, high-confidence hit)
  score >= score_medium OR  words <= medium  →  flash  (balanced)
  otherwise                                  →  pro    (complex / low-KB-confidence)

Model keys here must match the keys in config.GEMINI_MODELS exactly.
"""
from __future__ import annotations

from dataclasses import dataclass

from config import ROUTER


@dataclass
class RouteDecision:
    model_key: str   # "lite" | "flash" | "pro"
    reason: str


def route(query: str, retrieval_score: float, has_image: bool) -> RouteDecision:
    if has_image:
        return RouteDecision("flash", "image → vision model")

    words = len(query.split())

    if (retrieval_score >= ROUTER["score_high"]
            and words <= ROUTER["words_short"]):
        return RouteDecision(
            "lite",    # FIX: was "flash_lite" — key not present in GEMINI_MODELS → KeyError
            f"KB hit={retrieval_score:.2f} >= {ROUTER['score_high']}, "
            f"words={words} <= {ROUTER['words_short']}",
        )

    if (retrieval_score >= ROUTER["score_medium"]
            or words <= ROUTER["words_medium"]):
        return RouteDecision(
            "flash",
            f"KB hit={retrieval_score:.2f}, words={words}",
        )

    return RouteDecision(
        "pro",         # FIX: was "reasoning" — key not present in GEMINI_MODELS → KeyError
        f"low KB hit={retrieval_score:.2f}, complex query ({words} words)",
    )
