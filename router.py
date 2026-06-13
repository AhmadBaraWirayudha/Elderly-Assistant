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

    if retrieval_score >= ROUTER["score_high"] and words <= ROUTER["words_short"]:
        return RouteDecision("flash_lite", "high KB hit + short query")

    if retrieval_score >= ROUTER["score_medium"] or words <= ROUTER["words_medium"]:
        return RouteDecision("flash", "medium confidence or moderate length")

    return RouteDecision("reasoning", "low KB score + complex query")
