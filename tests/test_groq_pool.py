"""Groq key rotation, the 503 when every key is limited, and CORS on errors."""

import logging

import pytest

from rag_core.llm import AIBusy, BUSY_DETAIL, call_with_rotation, complete_text, get_api_keys, reset_clients
from tests.conftest import register


class RateLimitError(Exception):
    def __init__(self):
        super().__init__("limited")
        self.status_code = 429


class _Message:
    def __init__(self, content):
        self.content = content


class _Client:
    def __init__(self, key, calls):
        self.key = key
        self.calls = calls

    def invoke(self, prompt):
        self.calls.append(self.key)
        if self.key == "key-a":
            raise RateLimitError()
        return _Message(f"from-{self.key}")

    def bind(self, **_kwargs):
        return self


def _install(monkeypatch, keys, calls):
    monkeypatch.setenv("GROQ_API_KEYS", ",".join(keys))
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    reset_clients()

    def build(_size, api_key):
        return _Client(api_key, calls)

    monkeypatch.setattr("rag_core.llm._build_client", build)


def test_list_prefers_groq_api_keys_and_keeps_five(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "single-key")
    monkeypatch.setenv("GROQ_API_KEYS", "k1, k2, k3, k4, k5, k6, k1")
    assert get_api_keys() == ["k1", "k2", "k3", "k4", "k5"]


def test_single_key_fallback(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEYS", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "only-one")
    assert get_api_keys() == ["only-one"]


def test_round_robin_skips_a_rate_limited_key(monkeypatch):
    calls = []
    _install(monkeypatch, ["key-a", "key-b"], calls)
    assert complete_text("small", "hello") == "from-key-b"
    assert calls == ["key-a", "key-b"]
    # The next request starts on key-b. key-a is cooling, so it is not called again.
    assert complete_text("small", "again") == "from-key-b"
    assert calls == ["key-a", "key-b", "key-b"]


def test_all_keys_limited_raises_ai_busy_without_logging_the_key(monkeypatch, caplog):
    calls = []

    class Limited(_Client):
        def invoke(self, prompt):
            self.calls.append(self.key)
            error = RateLimitError()
            error.status_code = 429
            raise error

    monkeypatch.setenv("GROQ_API_KEYS", "secret-key-one,secret-key-two")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    reset_clients()

    def build(_size, api_key):
        return Limited(api_key, calls)

    monkeypatch.setattr("rag_core.llm._build_client", build)
    with caplog.at_level(logging.WARNING, logger="codelens.llm"):
        with pytest.raises(AIBusy) as caught:
            call_with_rotation("large", lambda client: client.invoke("prompt"))
    assert str(caught.value) == BUSY_DETAIL
    assert calls == ["secret-key-one", "secret-key-two"]
    assert "secret-key-one" not in caplog.text
    assert "secret-key-two" not in caplog.text
    # The cooled keys are not called again while the cooldown holds.
    with pytest.raises(AIBusy):
        call_with_rotation("large", lambda client: client.invoke("prompt"))
    assert calls == ["secret-key-one", "secret-key-two"]


async def test_ai_busy_is_503_and_errors_keep_cors_headers(client, monkeypatch):
    async def busy(*_args, **_kwargs):
        raise AIBusy()

    monkeypatch.setattr("rag_core.api.run_pipeline", busy)
    _body, headers = await register(client)
    headers = {**headers, "Origin": "https://codelens.vercel.app"}
    limited = await client.post("/ask", json={"query": "What is a stack?"}, headers=headers)
    assert limited.status_code == 503
    assert limited.json()["detail"] == BUSY_DETAIL
    assert limited.headers["access-control-allow-origin"] in {"*", "https://codelens.vercel.app"}

    async def explode(_user_id):
        raise RuntimeError("gsk_should_not_leak")

    monkeypatch.setattr("rag_core.api.persona_view", explode)
    broken = await client.get("/me/persona", headers=headers)
    assert broken.status_code == 500
    assert broken.json()["detail"] == "Something went wrong. Please try again."
    assert "gsk_should_not_leak" not in broken.text
    assert broken.headers["access-control-allow-origin"] in {"*", "https://codelens.vercel.app"}


def test_a_normal_error_is_not_treated_as_rate_limit(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "only-one")
    monkeypatch.delenv("GROQ_API_KEYS", raising=False)
    reset_clients()

    class Client:
        def invoke(self, _prompt):
            raise RuntimeError("model exploded")

        def bind(self, **_kwargs):
            return self

    monkeypatch.setattr("rag_core.llm._build_client", lambda _size, _key: Client())
    with pytest.raises(RuntimeError, match="model exploded"):
        complete_text("small", "hello")
