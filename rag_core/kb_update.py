"""Stage proposed knowledge-base text until a teacher approves it.

Web results are inserted into ``kb_pending`` only. ``write_kb_document`` is the
runtime path that adds a document to the Chroma collection ``codelens_kb``.
It runs when a teacher approves a pending note, creates a note with
``approve`` left on, bulk-approves, or accepts upload chunks. ``delete_kb_documents``
removes those vectors when the note is deleted, and when an approved note's
text is replaced. ``python -m rag_core.build_kb`` is the separate offline seed.

Editing a pending row and rejecting a row do not write to Chroma. If a write
fails, the row stays ``pending`` so a retry can still approve it.
"""

import asyncio
import logging
from datetime import datetime

from rag_core.kb_fields import KBInputError, validate_create, validate_patch
from rag_core.kb_files import (
    MAX_UPLOAD_BYTES,
    UploadRejected,
    chunk_text,
    extension_allowed,
    extract_note,
    filename_title,
    safe_filename,
)
from rag_core.mongo import utcnow
from rag_core.store import (
    attach_upload,
    delete_upload,
    find_kb,
    find_upload,
    insert_kb,
    insert_upload,
    kb_facets,
    kb_public_many,
    kb_public_one,
    list_pending_kb,
    list_uploads,
    remove_kb,
    search_kb_rows,
    set_kb_status,
    update_kb_fields,
    upload_public,
)

logger = logging.getLogger("codelens.kb")


class ChromaError(Exception):
    """Chroma refused a write or a delete. The Mongo status was not moved forward."""


class MissingUpload(LookupError):
    """No upload with that id."""


def write_kb_document(content: str, query: str, source: str | None) -> list[str]:
    """Add one approved note to Chroma. Do not call this from the web agent."""
    from langchain_core.documents import Document

    from rag_core.agents.retrieval import get_vectorstore

    ids = get_vectorstore().add_documents(
        [
            Document(
                page_content=content,
                metadata={"source": source or "web", "query": query or ""},
            )
        ]
    )
    if not isinstance(ids, list):
        return []
    return [str(item) for item in ids if item]


def delete_kb_documents(ids: list[str] | None) -> None:
    """Remove vectors previously returned by ``write_kb_document``."""
    cleaned = [str(item) for item in (ids or []) if item]
    if not cleaned:
        return
    from rag_core.agents.retrieval import get_vectorstore

    get_vectorstore().delete(ids=cleaned)


def _ids(value) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return []


async def _chroma_add(content: str, query: str, source: str | None) -> list[str]:
    try:
        raw = await asyncio.to_thread(write_kb_document, content or "", query or "", source)
    except Exception as exc:
        logger.exception("knowledge base write failed")
        raise ChromaError("Could not write to the knowledge base") from exc
    return _ids(raw)


async def _chroma_remove(ids: list[str] | None) -> None:
    cleaned = [str(item) for item in (ids or []) if item]
    if not cleaned:
        return
    try:
        await asyncio.to_thread(delete_kb_documents, cleaned)
    except Exception as exc:
        logger.exception("knowledge base delete failed")
        raise ChromaError("Could not remove the note from the knowledge base") from exc


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
        title=(query or "").strip() or None,
        origin="ai",
        note_type="concept",
    )
    logger.info("staged kb item id=%s proposed_by=%s", item_id, proposed_by)
    return item_id


async def pending_items() -> list[dict]:
    return await list_pending_kb()


async def edit_pending(item_id: str, content: str) -> dict:
    return await edit_kb(item_id, {"content": content})


async def edit_kb(item_id: str, patch: dict) -> dict:
    """Update a pending or approved note. Status does not change.

    An approved note is written to Chroma again when its text, title, or
    source changes. The previous vectors are removed after the new write.
    """
    fields = validate_patch(patch)
    doc = await find_kb(item_id)
    if doc is None:
        raise LookupError(item_id)
    if doc.get("status") not in {"pending", "approved"}:
        raise ValueError("Only a pending or approved item can be edited")
    if not fields:
        return await kb_public_one(doc)
    new_content = fields.get("content", doc.get("content") or "")
    new_query = fields.get("query", doc.get("query") or "")
    new_source = fields.get("source", doc.get("source"))
    chroma_changed = doc.get("status") == "approved" and (
        new_content != (doc.get("content") or "")
        or new_query != (doc.get("query") or "")
        or new_source != doc.get("source")
    )
    new_ids = None
    if chroma_changed:
        new_ids = await _chroma_add(new_content, new_query, new_source)
    updated = await update_kb_fields(item_id, fields, chroma_ids=new_ids)
    if chroma_changed:
        kept = set(new_ids or [])
        stale = [item for item in (doc.get("chroma_ids") or []) if item not in kept]
        try:
            await _chroma_remove(stale)
        except ChromaError:
            logger.exception("old knowledge base vectors were left in place id=%s", item_id)
    return await kb_public_one(updated)


async def approve_pending(item_id: str, reviewer_id: str) -> dict:
    """Write the pending text to Chroma, then mark it approved.

    The status stays ``pending`` if the vector write fails, so a retry can
    still approve it. A second approval of an already decided item is refused.
    """
    doc = await find_kb(item_id)
    if doc is None:
        raise LookupError(item_id)
    if doc.get("status") != "pending":
        raise ValueError("Only a pending item can be approved")
    ids = await _chroma_add(doc.get("content") or "", doc.get("query") or "", doc.get("source"))
    updated = await set_kb_status(item_id, "approved", reviewer_id, chroma_ids=ids)
    return await kb_public_one(updated)


async def reject_pending(item_id: str, reviewer_id: str, reason: str | None = None) -> dict:
    if reason is not None and not str(reason).strip():
        raise KBInputError("A reject reason is required")
    cleaned = str(reason).strip() if reason is not None else None
    try:
        updated = await set_kb_status(item_id, "rejected", reviewer_id, reject_reason=cleaned)
    except ValueError:
        raise ValueError("Only a pending item can be rejected") from None
    return await kb_public_one(updated)


async def create_kb_item(teacher: dict, body: dict) -> dict:
    """Teacher-authored note. ``approve`` defaults to true and writes Chroma.

    Origin is the caller. A teacher note can be stored pending when
    ``approve`` is false. Student and AI origins are not accepted on this
    route; those rows are staged elsewhere and stay pending until approve.
    """
    fields = validate_create(body)
    item_id = await insert_kb(
        content=fields["content"],
        source=fields["source"],
        proposed_by=teacher["id"],
        query=fields["query"],
        status="pending",
        title=fields["title"],
        topic=fields["topic"],
        tags=fields["tags"],
        difficulty=fields["difficulty"],
        note_type=fields["type"],
        origin="teacher",
        proposer_name=teacher.get("name"),
        proposer_role=teacher.get("role") or "teacher",
    )
    if not fields["approve"]:
        doc = await find_kb(item_id)
        return await kb_public_one(doc)
    ids = await _chroma_add(fields["content"], fields["query"], fields["source"])
    updated = await set_kb_status(item_id, "approved", teacher["id"], chroma_ids=ids)
    return await kb_public_one(updated)


async def delete_kb_item(item_id: str) -> dict:
    doc = await find_kb(item_id)
    if doc is None:
        raise LookupError(item_id)
    if doc.get("status") == "approved":
        await _chroma_remove(doc.get("chroma_ids") or [])
    removed = await remove_kb(item_id)
    if removed is None:
        raise LookupError(item_id)
    return {"id": item_id, "deleted": True}


async def bulk_review(teacher: dict, ids: list, action: str, reason: str | None) -> dict:
    if not ids:
        raise KBInputError("Choose at least one note")
    if action not in {"approve", "reject"}:
        raise KBInputError("Action must be approve or reject")
    if action == "reject" and not str(reason or "").strip():
        raise KBInputError("A reject reason is required")
    updated = []
    failed = []
    for raw in ids:
        item_id = str(raw)
        try:
            if action == "approve":
                item = await approve_pending(item_id, teacher["id"])
            else:
                item = await reject_pending(item_id, teacher["id"], reason)
            updated.append(item)
        except LookupError:
            failed.append({"id": item_id, "detail": "Knowledge item not found"})
        except KBInputError as exc:
            failed.append({"id": item_id, "detail": str(exc)})
        except ValueError:
            failed.append({"id": item_id, "detail": "Only a pending item can be reviewed"})
        except ChromaError as exc:
            failed.append({"id": item_id, "detail": str(exc)})
        except Exception:
            logger.exception("bulk kb review failed id=%s", item_id)
            failed.append({"id": item_id, "detail": "Could not write to the knowledge base"})
    return {"updated": updated, "failed": failed}


def parse_day(value: str, *, end: bool) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        day = datetime.strptime(text, "%Y-%m-%d")
    except ValueError as exc:
        raise KBInputError("Dates must be YYYY-MM-DD") from exc
    if end:
        return day.replace(hour=23, minute=59, second=59)
    return day


async def search_library(filters: dict) -> dict:
    status = (filters.get("status") or "").strip()
    if status and status not in {"pending", "approved", "rejected"}:
        raise KBInputError("Unknown status")
    start = parse_day(filters.get("from") or "", end=False)
    end = parse_day(filters.get("to") or "", end=True)
    page = max(1, int(filters.get("page") or 1))
    page_size = min(50, max(1, int(filters.get("page_size") or 8)))
    rows = await search_kb_rows(
        q=(filters.get("q") or "").strip(),
        topic=(filters.get("topic") or "").strip(),
        tag=(filters.get("tag") or "").strip().lower(),
        note_type=(filters.get("type") or "").strip(),
        source=(filters.get("source") or "").strip(),
        start=start,
        end=end,
    )
    counts = {"pending": 0, "approved": 0, "rejected": 0}
    matched = []
    for row in rows:
        row_status = row.get("status") or "pending"
        if row_status in counts:
            counts[row_status] += 1
        if status and row_status != status:
            continue
        matched.append(row)
    pending_oldest = status == "pending"

    def stamp(row: dict):
        if pending_oldest:
            return row.get("created_at") or datetime.min
        return row.get("updated_at") or row.get("created_at") or datetime.min

    matched.sort(key=lambda row: (stamp(row), str(row["_id"])), reverse=not pending_oldest)
    total = len(matched)
    pages = max(1, (total + page_size - 1) // page_size) if total else 1
    page = min(page, pages)
    start_at = (page - 1) * page_size
    items = await kb_public_many(matched[start_at : start_at + page_size])
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "counts": counts,
        "facets": await kb_facets(),
    }


async def save_upload(teacher: dict, filename: str | None, media_type: str, raw: bytes) -> dict:
    name = safe_filename(filename)
    if not extension_allowed(name):
        raise UploadRejected(415, "Upload a PDF, DOCX, TXT, or MD file.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise UploadRejected(413, "That file is larger than 5 MB.")
    try:
        chunks = chunk_text(extract_note(raw, name))
        status = "chunked"
        error = ""
    except ValueError as exc:
        chunks = []
        status = "failed"
        error = str(exc)
    doc = {
        "filename": name,
        "media_type": media_type or "",
        "size": len(raw),
        "status": status,
        "progress": 100,
        "error": error,
        "created_at": utcnow(),
        "kb_item_id": None,
        "chunks": chunks,
        "uploaded_by": teacher["id"],
    }
    upload_id = await insert_upload(doc)
    stored = await find_upload(upload_id)
    return upload_public(stored or doc)


async def uploads() -> list[dict]:
    return [upload_public(row) for row in await list_uploads()]


async def approve_upload(teacher: dict, upload_id: str, body: dict) -> dict:
    upload = await find_upload(upload_id)
    if upload is None:
        raise MissingUpload(upload_id)
    if upload.get("kb_item_id"):
        raise ValueError("That upload is already in the library")
    if upload.get("status") != "chunked":
        raise ValueError("Only a chunked upload can be approved")
    chunks = upload.get("chunks") or []
    wanted = body.get("chunk_indexes")
    if wanted is None:
        chosen = list(chunks)
    else:
        indexes = set()
        for value in wanted:
            try:
                indexes.add(int(value))
            except (TypeError, ValueError):
                continue
        chosen = [chunk for chunk in chunks if int(chunk.get("index", -1)) in indexes]
    if not chosen:
        raise KBInputError("Choose at least one chunk")
    content = "\n\n".join((chunk.get("content") or "").strip() for chunk in chosen).strip()
    if not content:
        raise KBInputError("Choose at least one chunk")
    tags = body.get("tags")
    fields = validate_create(
        {
            "title": str(body.get("title") or "").strip() or filename_title(upload.get("filename")),
            "content": content,
            "topic": str(body.get("topic") or "").strip() or "Upload",
            "tags": tags if tags else ["upload"],
            "difficulty": body.get("difficulty"),
            "source": "upload",
            "type": "document",
            "approve": True,
        }
    )
    item_id = await insert_kb(
        content=fields["content"],
        source="upload",
        proposed_by=teacher["id"],
        query=fields["query"],
        status="pending",
        title=fields["title"],
        topic=fields["topic"],
        tags=fields["tags"],
        difficulty=fields["difficulty"],
        note_type="document",
        origin="upload",
        proposer_name=teacher.get("name"),
        proposer_role=teacher.get("role") or "teacher",
    )
    try:
        ids = await _chroma_add(fields["content"], fields["query"], "upload")
    except ChromaError:
        await remove_kb(item_id)
        raise
    updated = await set_kb_status(item_id, "approved", teacher["id"], chroma_ids=ids)
    await attach_upload(upload_id, item_id)
    stored = await find_upload(upload_id)
    return {"upload": upload_public(stored), "item": await kb_public_one(updated)}


async def discard_upload(upload_id: str) -> dict:
    upload = await find_upload(upload_id)
    if upload is None:
        raise MissingUpload(upload_id)
    if upload.get("kb_item_id"):
        raise ValueError("That upload is already in the library")
    if not await delete_upload(upload_id):
        raise MissingUpload(upload_id)
    return {"id": upload_id, "deleted": True}
