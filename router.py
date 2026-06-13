"""
router.py — Decides which Gemini model to use for a given query.

Decision tree:
  Image present  →  flash  (vision is always Flash)
  score >= 0.80 AND words <= 40  →  flash_lite  (high KB confidence, short query)
  score >= 0.55 OR  words <= 80  →  flash       (medium confidence or moderate length)
  otherwise                       →  reasoning   (low confidence + long/complex)
"""

from __future__ import annotations
from dataclasses import dataclass
from config import ROUTER

@dataclass
class RouteDecision:
    model_key: str
    reason: str

def route(query: str, retrieval_score: float, has_image: bool) -> RouteDecision:
    if has_image:
        return RouteDecision("flash", "image → vision model")

    words = len(query.split())

      if (retrieval_score >= ROUTER["score_high"]
            and words <= ROUTER["words_short"]):
        return RouteDecision(
            "flash_lite",
            f"KB hit={retrieval_score:.2f} >= {ROUTER['score_high']}, "
            f"words={words} <= {ROUTER['words_short']}"
        )

    if (retrieval_score >= ROUTER["score_medium"]
            or words <= ROUTER["words_medium"]):
        return RouteDecision(
            "flash",
            f"KB hit={retrieval_score:.2f}, words={words}"
        )

    return RouteDecision(
        "reasoning",
        f"low KB hit={retrieval_score:.2f}, complex query ({words} words)"
      )
