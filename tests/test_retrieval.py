"""Embedding warmup stays off during pytest and runs outside it."""

import os

from rag_core.agents.retrieval import warm_retrieval


def test_warm_retrieval_skips_during_pytest(monkeypatch):
    called = []
    monkeypatch.setattr(
        "rag_core.agents.retrieval.get_embeddings",
        lambda: called.append("embeddings"),
    )
    warm_retrieval()
    assert called == []
    assert os.getenv("PYTEST_CURRENT_TEST")


def test_warm_retrieval_loads_the_model_outside_pytest(monkeypatch, tmp_path):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    kb = tmp_path / "kb"
    kb.mkdir()
    (kb / "chroma.sqlite3").write_text("", encoding="utf-8")
    monkeypatch.setenv("CODELENS_KB", str(kb))

    class FakeEmbeddings:
        def embed_query(self, text):
            return [0.1]

    seen = []
    monkeypatch.setattr("rag_core.agents.retrieval.get_embeddings", lambda: FakeEmbeddings())
    monkeypatch.setattr(
        "rag_core.agents.retrieval.get_context",
        lambda query, k=2: seen.append((query, k)) or "note",
    )

    warm_retrieval()
    assert seen == [("NameError", 2)]


def test_low_memory_embeddings_use_a_batch_of_one(monkeypatch):
    import sys
    import types

    import rag_core.agents.retrieval as retrieval

    monkeypatch.setenv("CODELENS_LOW_MEMORY", "1")
    monkeypatch.setattr(retrieval, "_embeddings", None)
    captured = {}

    class Fake:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    module = types.ModuleType("langchain_huggingface")
    module.HuggingFaceEmbeddings = Fake
    monkeypatch.setitem(sys.modules, "langchain_huggingface", module)
    try:
        retrieval.get_embeddings()
    finally:
        monkeypatch.setattr(retrieval, "_embeddings", None)
    assert captured["model_name"] == retrieval.EMBEDDING_MODEL
    assert captured["model_kwargs"] == {"device": "cpu"}
    assert captured["encode_kwargs"] == {"batch_size": 1}


def test_warm_retrieval_skips_a_missing_index(monkeypatch, tmp_path):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("CODELENS_KB", str(tmp_path / "absent"))

    class FakeEmbeddings:
        def embed_query(self, text):
            return [0.1]

    seen = []
    monkeypatch.setattr("rag_core.agents.retrieval.get_embeddings", lambda: FakeEmbeddings())
    monkeypatch.setattr(
        "rag_core.agents.retrieval.get_context",
        lambda query, k=2: seen.append(query),
    )

    warm_retrieval()
    assert seen == []
