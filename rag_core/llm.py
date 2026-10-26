"""Shared Groq clients.

Every model call goes through this pool. ``GROQ_API_KEYS`` is a comma-separated
list (three to five keys in production). A single ``GROQ_API_KEY`` still works
and is the fallback when the list is empty. Each request starts on the next
key. A 429 rotates to the following key immediately. The Groq SDK's own
retries stay off so a limited key is not hammered. A key that just returned
429 sits out for a short cooldown. If every key is limited, callers get
``AIBusy``, which the API turns into HTTP 503.

Key values are never written to the log.
"""

import json
import logging
import os
import re
import threading
import time

logger = logging.getLogger("codelens.llm")

MODEL_SMALL = "openai/gpt-oss-20b"
MODEL_LARGE = "openai/gpt-oss-120b"
BUSY_DETAIL = "AI service is busy, please try again in a few seconds"
MAX_KEYS = 5

_clients: dict = {}
_env_loaded = False
_lock = threading.Lock()
_cursor = 0
_cooldown_until: dict[int, float] = {}
_key_fingerprint: tuple[int, ...] = ()


class AIBusy(Exception):
    """Every configured Groq key is rate-limited."""

    def __init__(self, detail: str = BUSY_DETAIL):
        self.detail = detail
        super().__init__(detail)


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


def _cooldown_seconds() -> float:
    raw = os.getenv("GROQ_KEY_COOLDOWN_SECONDS", "15")
    try:
        seconds = float(raw)
    except ValueError:
        seconds = 15.0
    return min(max(seconds, 1.0), 120.0)


def get_api_keys() -> list[str]:
    """Configured keys, list first, then the single-key fallback. At most five."""
    _load_env()
    raw = os.getenv("GROQ_API_KEYS", "")
    keys: list[str] = []
    if raw.strip():
        keys = [part.strip() for part in raw.split(",") if part.strip()]
    if not keys:
        single = (os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API") or "").strip()
        if single:
            keys = [single]
    unique: list[str] = []
    seen: set[str] = set()
    for key in keys:
        if key in seen:
            continue
        seen.add(key)
        unique.append(key)
    if len(unique) > MAX_KEYS:
        logger.warning("groq pool ignoring extra keys count=%s kept=%s", len(unique), MAX_KEYS)
        unique = unique[:MAX_KEYS]
    return unique


def get_api_key() -> str | None:
    """First configured key, for callers that only need to know one is set."""
    keys = get_api_keys()
    return keys[0] if keys else None


def _fingerprint(keys: list[str]) -> tuple[int, ...]:
    """Identify the key set without keeping the secret in the log line."""
    return tuple(hash(key) for key in keys)


def _model(size: str) -> tuple[str, int]:
    if size == "small":
        return MODEL_SMALL, 2048
    if size == "large":
        return MODEL_LARGE, 4096
    raise ValueError(f"Unknown model size: {size}")


def _build_client(size: str, api_key: str):
    """One ChatGroq. ``max_retries=0`` stops the SDK from sleeping on 429."""
    from langchain_groq import ChatGroq

    model, max_tokens = _model(size)
    kwargs = {
        "model": model,
        "api_key": api_key,
        "temperature": 0,
        "max_tokens": max_tokens,
        "max_retries": 0,
    }
    try:
        client = ChatGroq(**kwargs)
    except TypeError:
        kwargs.pop("max_retries", None)
        client = ChatGroq(**kwargs)
        inner = getattr(client, "client", None)
        if inner is not None and hasattr(inner, "max_retries"):
            inner.max_retries = 0
    return client


def _sync_pool(keys: list[str]) -> None:
    global _key_fingerprint, _cursor
    fingerprint = _fingerprint(keys)
    if fingerprint == _key_fingerprint and _clients:
        return
    _clients.clear()
    _cooldown_until.clear()
    _cursor = 0
    _key_fingerprint = fingerprint
    logger.info("groq pool configured keys=%s", len(keys))


def _client_for(size: str, index: int, api_key: str):
    slot = (size, index)
    client = _clients.get(slot)
    if client is None:
        client = _build_client(size, api_key)
        _clients[slot] = client
        model, _tokens = _model(size)
        logger.info("built groq client size=%s model=%s key_index=%s", size, model, index)
    return client


def _is_rate_limit(exc: BaseException) -> bool:
    status = getattr(exc, "status_code", None)
    if status == 429:
        return True
    response = getattr(exc, "response", None)
    if getattr(response, "status_code", None) == 429:
        return True
    return type(exc).__name__ in {"RateLimitError", "RateLimit"}


def _cooling(index: int, now: float) -> bool:
    return _cooldown_until.get(index, 0.0) > now


def _cool(index: int, now: float) -> None:
    _cooldown_until[index] = now + _cooldown_seconds()
    logger.warning("groq key cooling key_index=%s", index)


def call_with_rotation(size: str, run):
    """Run ``run(client)`` on the next live key. Rotate once on 429."""
    global _cursor
    if size not in ("small", "large"):
        raise ValueError(f"Unknown model size: {size}")
    keys = get_api_keys()
    if not keys:
        raise RuntimeError("GROQ_API_KEY is not set")
    with _lock:
        _sync_pool(keys)
        start = _cursor % len(keys)
        _cursor += 1
        now = time.monotonic()
        order = []
        for offset in range(len(keys)):
            index = (start + offset) % len(keys)
            if _cooling(index, now):
                continue
            order.append(index)
        if not order:
            raise AIBusy()
        clients = [(index, _client_for(size, index, keys[index])) for index in order]

    last_error: BaseException | None = None
    for index, client in clients:
        try:
            return run(client)
        except AIBusy:
            raise
        except Exception as exc:
            if not _is_rate_limit(exc):
                raise
            last_error = exc
            with _lock:
                _cool(index, time.monotonic())
            logger.warning("groq rate limit size=%s key_index=%s; trying the next key", size, index)
    del last_error
    raise AIBusy()


class _Bound:
    def __init__(self, size: str, options: dict):
        self.size = size
        self.options = options

    def invoke(self, prompt, *args, **kwargs):
        def run(client):
            try:
                bound = client.bind(**self.options)
            except Exception:
                bound = client
            return bound.invoke(prompt, *args, **kwargs)

        return call_with_rotation(self.size, run)


class _RotatingLLM:
    """Drop-in stand-in for one ChatGroq. ``invoke`` rotates keys."""

    def __init__(self, size: str):
        self.size = size

    def invoke(self, prompt, *args, **kwargs):
        def run(client):
            return client.invoke(prompt, *args, **kwargs)

        return call_with_rotation(self.size, run)

    def bind(self, **kwargs):
        return _Bound(self.size, kwargs)


def get_llm(size: str = "small"):
    """Return a rotating client for ``small`` or ``large``."""
    if size not in ("small", "large"):
        raise ValueError(f"Unknown model size: {size}")
    return _RotatingLLM(size)


def init_clients() -> None:
    """Build a client per key and size. Called from the FastAPI lifespan."""
    keys = get_api_keys()
    if not keys:
        logger.warning("No Groq API key is set; LLM clients deferred until first use")
        return
    with _lock:
        _sync_pool(keys)
        for size in ("small", "large"):
            for index, key in enumerate(keys):
                _client_for(size, index, key)
    logger.info("groq pool ready keys=%s", len(keys))


def reset_clients() -> None:
    """Drop cached clients. Tests use this after changing the environment."""
    global _cursor, _key_fingerprint
    with _lock:
        _clients.clear()
        _cooldown_until.clear()
        _cursor = 0
        _key_fingerprint = ()


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
    def run(client):
        return message_text(client.invoke(prompt)).strip()

    return call_with_rotation(size, run)


def complete_json(size: str, prompt: str) -> dict:
    """Ask the model for one JSON object."""

    def run(client):
        try:
            runnable = client.bind(response_format={"type": "json_object"})
        except Exception:
            runnable = client
        message = runnable.invoke(prompt)
        return parse_json_content(message_text(message))

    return call_with_rotation(size, run)
