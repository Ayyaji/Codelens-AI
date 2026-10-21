"""Retrieval shared by the tutoring agents.

The embedding client is built once and reused. The API loads it during startup
so the first POST /ask is not the request that imports the model.
"""

import logging
import os
import time

from rag_core.config import get_kb_dir

logger = logging.getLogger("codelens.retrieval")

# Short name sentence-transformers resolves to sentence-transformers/all-MiniLM-L6-v2.
# Keep this string stable: a built Chroma index is tied to the model that wrote it.
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

_embeddings = None
_vectorstore = None


def get_embeddings():
    global _embeddings
    if _embeddings is None:
        from langchain_huggingface import HuggingFaceEmbeddings

        # CODELENS_LOW_MEMORY=1 is set in the production image. batch_size 1
        # keeps the encode step from allocating a large tensor on a 1–2 GiB
        # instance. The vectors match the default encoder; only the batch changes.
        kwargs = {"model_name": EMBEDDING_MODEL}
        low_memory = os.getenv("CODELENS_LOW_MEMORY") == "1"
        if low_memory:
            kwargs["model_kwargs"] = {"device": "cpu"}
            kwargs["encode_kwargs"] = {"batch_size": 1}
        _embeddings = HuggingFaceEmbeddings(**kwargs)
        logger.info("built embedding client model=%s low_memory=%s", EMBEDDING_MODEL, low_memory)
    return _embeddings


def get_vectorstore():
    """Open the local Chroma index, reusing the process-wide embedding client."""
    global _vectorstore
    if _vectorstore is None:
        from langchain_chroma import Chroma

        _vectorstore = Chroma(
            persist_directory=get_kb_dir(),
            embedding_function=get_embeddings(),
        )
    return _vectorstore


def _index_ready() -> bool:
    return os.path.isfile(os.path.join(get_kb_dir(), "chroma.sqlite3"))


def warm_retrieval() -> None:
    """Import the embedding model and open the index if build_kb has been run.

    Loading all-MiniLM-L6-v2 is the slow part of the first guidance request
    (import, weights, and the first encode). Doing it here moves that wait to
    process startup. A missing package or an unbuilt index is logged and does
    not stop the API: JD upload and the test do not need this model.

    The pytest suite sets PYTEST_CURRENT_TEST and does not ship the model, so
    this returns immediately there.
    """
    if os.getenv("PYTEST_CURRENT_TEST"):
        return
    started = time.perf_counter()
    try:
        logger.info("loading embedding model %s", EMBEDDING_MODEL)
        get_embeddings().embed_query("NameError")
        if _index_ready():
            get_context("NameError")
        logger.info("embedding model ready in %.2fs", time.perf_counter() - started)
    except Exception as exc:
        logger.warning("embedding warmup skipped: %s", exc)


def get_context(query: str, k: int = 2) -> str:
    """Return knowledge-base text for a tutoring prompt. Empty if the KB is missing."""
    try:
        docs = get_vectorstore().as_retriever(search_kwargs={"k": k}).invoke(query)
        return "\n".join(doc.page_content for doc in docs)
    except Exception as exc:
        logger.warning("retrieval unavailable: %s", exc)
        return ""
