"""Retrieval shared by the tutoring agents. The embedding client is built on first use."""

import logging

from rag_core.config import get_kb_dir

logger = logging.getLogger("codelens.retrieval")

_embeddings = None
_vectorstore = None


def get_embeddings():
    global _embeddings
    if _embeddings is None:
        from langchain_huggingface import HuggingFaceEmbeddings

        _embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        logger.info("built embedding client model=all-MiniLM-L6-v2")
    return _embeddings


def get_context(query: str, k: int = 2) -> str:
    """Return knowledge-base text for a tutoring prompt. Empty if the KB is missing."""
    global _vectorstore
    try:
        from langchain_chroma import Chroma

        if _vectorstore is None:
            _vectorstore = Chroma(
                persist_directory=get_kb_dir(),
                embedding_function=get_embeddings(),
            )
        docs = _vectorstore.as_retriever(search_kwargs={"k": k}).invoke(query)
        return "\n".join(doc.page_content for doc in docs)
    except Exception as exc:
        logger.warning("retrieval unavailable: %s", exc)
        return ""
