"""Route a guidance question. Obvious cases stay in plain code; the small model handles the rest."""

import re

from rag_core.judgment import extract_error_type
from rag_core.timing import log_latency

_HINT = re.compile(r"\b(hint|clue)\b", re.IGNORECASE)
_VALID = {"debug", "concept", "hint", "web"}


def _heuristic(query: str) -> str | None:
    if _HINT.search(query):
        return "hint"
    if extract_error_type(query):
        return "debug"
    return None


def _llm_route(query: str) -> str:
    from rag_core.llm import complete_text

    prompt = f"""You are the query router for CodeLens AI, an interview-readiness assistant.
Debugging help is part of guidance. Classify the student query into exactly one category:

- debug: an error, exception, or bug in their code
- concept: a programming or interview concept they want explained
- hint: they explicitly ask for a hint or clue, not a full answer
- web: the query is outside programming and interview preparation

Respond with only one word: debug, concept, hint, or web.

Student query: {query}

Category:"""
    response = complete_text("small", prompt).strip().lower()
    word = response.split()[0].strip(".,:;") if response else ""
    if word not in _VALID:
        return "debug"
    return word


def route_query(query: str) -> str:
    """Return debug, concept, hint, or web."""
    with log_latency("router") as info:
        guessed = _heuristic(query)
        if guessed:
            info["llm"] = "no"
            return guessed
        info["llm"] = "yes"
        return _llm_route(query)
