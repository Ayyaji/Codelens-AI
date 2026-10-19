"""Shared Groq clients.

Clients are built on application startup (see init_clients), not at import.
Routing and parsing use the small model. Explanations use the larger one.

llama-3.3-70b-versatile and llama-3.1-8b-instant were retired for Groq
self-serve tiers on 2026-08-16. The ids below are the production replacements.
"""

import json
import logging
import os
import re

logger = logging.getLogger("codelens.llm")

MODEL_SMALL = "openai/gpt-oss-20b"
MODEL_LARGE = "openai/gpt-oss-120b"

_clients: dict = {}
_env_loaded = False


def _load_env() -> None:
    global _env_loaded
    if _env_loaded:
        return
    _env_loaded = True
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass


def get_api_key() -> str | None:
    _load_env()
    return os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API")


def get_llm(size: str = "small"):
    """Return the shared client for ``small`` or ``large``."""
    if size not in ("small", "large"):
        raise ValueError(f"Unknown model size: {size}")
    if size not in _clients:
        from langchain_groq import ChatGroq

        key = get_api_key()
        if not key:
            raise RuntimeError("GROQ_API_KEY is not set")
        model = MODEL_SMALL if size == "small" else MODEL_LARGE
        max_tokens = 2048 if size == "small" else 4096
        _clients[size] = ChatGroq(
            model=model,
            api_key=key,
            temperature=0,
            max_tokens=max_tokens,
        )
        logger.info("built groq client size=%s model=%s", size, model)
    return _clients[size]


def init_clients() -> None:
    """Build both Groq clients. Called from the FastAPI lifespan."""
    if not get_api_key():
        logger.warning("GROQ_API_KEY is not set; LLM clients deferred until first use")
        return
    get_llm("small")
    get_llm("large")


def reset_clients() -> None:
    _clients.clear()


def message_text(message) -> str:
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                parts.append(str(block.get("text") or block.get("content") or ""))
        return "".join(parts)
    return str(content)


def parse_json_content(text: str) -> dict:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end < start:
            raise
        data = json.loads(cleaned[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("Model response was not a JSON object")
    return data


def complete_text(size: str, prompt: str) -> str:
    return message_text(get_llm(size).invoke(prompt)).strip()


def complete_json(size: str, prompt: str) -> dict:
    """Ask the model for one JSON object."""
    llm = get_llm(size)
    try:
        runnable = llm.bind(response_format={"type": "json_object"})
    except Exception:
        runnable = llm
    message = runnable.invoke(prompt)
    return parse_json_content(message_text(message))
