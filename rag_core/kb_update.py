"""Stage proposed knowledge-base text until a teacher approves it.

Web results and any other proposal are inserted into ``kb_pending`` only.
``write_kb_document`` is the one runtime path that adds a document to Chroma,
and only ``approve_pending`` calls it. ``python -m rag_core.build_kb`` is the
separate, offline seed of the project's own debugging notes.
"""

import asyncio
import logging

from rag_core.store import insert_kb, list_pending_kb, set_kb_status, update_kb_content

logger = logging.getLogger("codelens.kb")


def write_kb_document(content: str, query: str, source: str | None) -> None:
    """Add one approved note to Chroma. Do not call this from the web agent."""
    from langchain_core.documents import Document

    from rag_core.agents.retrieval import get_vectorstore

    get_vectorstore().add_documents(
        [
            Document(
                page_content=content,
                metadata={"source": source or "web", "query": query or ""},
            )
        ]
    )


async def stage_for_approval(
    query: str,
    content: str,
    source: str | None = None,
    proposed_by: str | None = None,
) -> str:
    """Queue text for a teacher. This never writes to Chroma."""
    item_id = await insert_kb(
        content=content,
        source=source,
        proposed_by=proposed_by,
        query=query,
        status="pending",
    )
    logger.info("staged kb item id=%s proposed_by=%s", item_id, proposed_by)
    return item_id


async def pending_items() -> list[dict]:
    return await list_pending_kb()


async def edit_pending(item_id: str, content: str) -> dict:
    return await update_kb_content(item_id, content)


async def approve_pending(item_id: str, reviewer_id: str) -> dict:
    """Write the pending text to Chroma, then mark it approved.

    The status stays ``pending`` if the vector write fails, so a retry can
    still approve it. A second approval of an already decided item is refused.
    """
    from rag_core.store import find_kb

    doc = await find_kb(item_id)
    if doc is None:
        raise LookupError(item_id)
    if doc.get("status") != "pending":
        raise ValueError("Only a pending item can be approved")
    await asyncio.to_thread(
        write_kb_document,
        doc.get("content") or "",
        doc.get("query") or "",
        doc.get("source"),
    )
    updated = await set_kb_status(item_id, "approved", reviewer_id)
    from rag_core.store import kb_public

    return kb_public(updated)


async def reject_pending(item_id: str, reviewer_id: str) -> dict:
    from rag_core.store import kb_public

    try:
        updated = await set_kb_status(item_id, "rejected", reviewer_id)
    except ValueError:
        raise ValueError("Only a pending item can be rejected") from None
    return kb_public(updated)
