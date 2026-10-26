"""Teacher knowledge-base library: search, create, edit, delete, bulk, and uploads."""

import io
import zipfile
from datetime import datetime, timezone

import pytest

from rag_core.kb_files import chunk_text
from tests.conftest import register
from tests.test_auth import _teacher


def _note(**overrides):
    body = {
        "title": "B-tree pages",
        "content": "Leaf nodes hold the keys.",
        "topic": "Indexes",
        "tags": ["SQL", "B-Tree"],
        "difficulty": "medium",
        "source": "textbook",
        "type": "concept",
        "approve": True,
    }
    body.update(overrides)
    return body


def _spy(monkeypatch):
    written = []
    deleted = []

    def write(content, query, source):
        written.append((content, query, source))
        return [f"vec-{len(written)}"]

    def remove(ids):
        deleted.extend(ids)

    monkeypatch.setattr("rag_core.kb_update.write_kb_document", write)
    monkeypatch.setattr("rag_core.kb_update.delete_kb_documents", remove)
    return written, deleted


def _today():
    return datetime.now(timezone.utc).date().isoformat()


def test_chunks_split_on_headings_and_blank_lines():
    chunks = chunk_text("# Joins\n\nAn inner join keeps matches.\n\n# Filters\n\nWHERE runs later.")
    assert [chunk["title"] for chunk in chunks] == ["Joins", "Filters"]
    assert chunks[0]["index"] == 0
    assert "inner join" in chunks[0]["content"]
    assert chunks[1]["content"].startswith("# Filters")


async def test_student_cannot_use_the_library(client):
    _body, headers = await register(client)
    assert (await client.get("/teacher/kb", headers=headers)).status_code == 403
    assert (await client.post("/teacher/kb", json=_note(), headers=headers)).status_code == 403
    assert (await client.post("/teacher/kb/bulk", json={"ids": ["x"], "action": "approve"}, headers=headers)).status_code == 403
    assert (await client.get("/teacher/kb/uploads", headers=headers)).status_code == 403
    assert (await client.delete("/teacher/kb/uploads/abc", headers=headers)).status_code == 403
    created = {"detail": "Teacher access required"}
    assert (await client.get("/teacher/kb", headers=headers)).json()["detail"] == created["detail"]


async def test_create_writes_chroma_and_filters(client, monkeypatch):
    written, deleted = _spy(monkeypatch)
    _body, headers = await register(client)
    _teacher_body, teacher_headers = await _teacher(client)

    pending = await client.post("/teacher/kb", json=_note(title="Pending note", approve=False), headers=teacher_headers)
    assert pending.status_code == 200, pending.text
    assert pending.json()["status"] == "pending"
    assert pending.json()["origin"] == "teacher"
    assert pending.json()["proposer_name"] == "Ada Rao"
    assert pending.json()["tags"] == ["sql", "b-tree"]
    assert written == []

    approved = await client.post("/teacher/kb", json=_note(), headers=teacher_headers)
    assert approved.status_code == 200, approved.text
    item = approved.json()
    assert item["status"] == "approved"
    assert item["query"] == "B-tree pages"
    assert written == [("Leaf nodes hold the keys.", "B-tree pages", "textbook")]
    assert deleted == []

    listed = await client.get("/teacher/kb", params={"q": "leaf", "status": "approved"}, headers=teacher_headers)
    assert listed.status_code == 200
    page = listed.json()
    assert page["total"] == 1
    assert page["items"][0]["id"] == item["id"]
    assert page["counts"] == {"pending": 1, "approved": 1, "rejected": 0}
    assert "Indexes" in page["facets"]["topics"]
    assert "sql" in page["facets"]["tags"]

    both = await client.get("/teacher/kb", params={"topic": "Indexes"}, headers=teacher_headers)
    assert both.json()["counts"] == {"pending": 1, "approved": 1, "rejected": 0}
    assert both.json()["total"] == 2

    today = _today()
    dated = await client.get(
        "/teacher/kb",
        params={"from": today, "to": today, "tag": "SQL", "type": "concept", "source": "textbook"},
        headers=teacher_headers,
    )
    assert dated.status_code == 200
    assert dated.json()["total"] == 2

    outside = await client.get("/teacher/kb", params={"from": "2001-01-01", "to": "2001-01-02"}, headers=teacher_headers)
    assert outside.json()["total"] == 0
    assert (await client.get("/teacher/kb", params={"from": "13-01-2026"}, headers=teacher_headers)).status_code == 422
    assert (await client.get("/teacher/kb", params={"status": "nope"}, headers=teacher_headers)).status_code == 422
    assert (await client.get("/teacher/kb", params={"page_size": 0}, headers=teacher_headers)).status_code == 422

    one = await client.get(f"/teacher/kb/{item['id']}", headers=teacher_headers)
    assert one.status_code == 200
    assert one.json()["title"] == "B-tree pages"
    assert (await client.get("/teacher/kb/missing", headers=teacher_headers)).status_code == 404
    assert (await client.get("/teacher/kb", headers=headers)).status_code == 403


async def test_pending_queue_stays_oldest_first(client, monkeypatch):
    _spy(monkeypatch)
    _teacher_body, teacher_headers = await _teacher(client)
    first = await client.post(
        "/teacher/kb",
        json=_note(title="First", content="one", approve=False),
        headers=teacher_headers,
    )
    second = await client.post(
        "/teacher/kb",
        json=_note(title="Second", content="two", approve=False),
        headers=teacher_headers,
    )
    page = await client.get("/teacher/kb", params={"status": "pending", "page_size": 1, "page": 5}, headers=teacher_headers)
    assert page.json()["page"] == 2
    assert page.json()["items"][0]["title"] == "Second"
    assert page.json()["total"] == 2
    oldest = await client.get("/teacher/kb", params={"status": "pending", "page_size": 1, "page": 1}, headers=teacher_headers)
    assert oldest.json()["items"][0]["id"] == first.json()["id"]
    legacy = await client.get("/teacher/kb/pending", headers=teacher_headers)
    assert [row["id"] for row in legacy.json()][:2] == [first.json()["id"], second.json()["id"]]


async def test_edit_delete_and_chroma_replacement(client, monkeypatch):
    written, deleted = _spy(monkeypatch)
    _teacher_body, teacher_headers = await _teacher(client)
    created = await client.post("/teacher/kb", json=_note(approve=False), headers=teacher_headers)
    item_id = created.json()["id"]

    edited = await client.put(
        f"/teacher/kb/{item_id}",
        json={"content": "teacher edited notes", "title": "B-tree pages", "topic": "Indexes"},
        headers=teacher_headers,
    )
    assert edited.status_code == 200
    assert edited.json()["status"] == "pending"
    assert written == []

    approved = await client.post(f"/teacher/kb/{item_id}/approve", headers=teacher_headers)
    assert approved.status_code == 200
    assert written == [("teacher edited notes", "B-tree pages", "textbook")]

    tags_only = await client.put(
        f"/teacher/kb/{item_id}",
        json={"tags": ["indexes"]},
        headers=teacher_headers,
    )
    assert tags_only.status_code == 200
    assert tags_only.json()["status"] == "approved"
    assert len(written) == 1
    assert deleted == []

    replaced = await client.put(
        f"/teacher/kb/{item_id}",
        json={"content": "Root pages point at leaves.", "title": "B-tree pages"},
        headers=teacher_headers,
    )
    assert replaced.status_code == 200
    assert written[1][0] == "Root pages point at leaves."
    assert deleted == ["vec-1"]

    removed = await client.delete(f"/teacher/kb/{item_id}", headers=teacher_headers)
    assert removed.status_code == 200
    assert removed.json() == {"id": item_id, "deleted": True}
    assert "vec-2" in deleted
    assert (await client.get(f"/teacher/kb/{item_id}", headers=teacher_headers)).status_code == 404


async def test_chroma_failure_leaves_the_row_pending(client, monkeypatch):
    def boom(content, query, source):
        raise RuntimeError("chroma down")

    monkeypatch.setattr("rag_core.kb_update.write_kb_document", boom)
    _teacher_body, teacher_headers = await _teacher(client)
    failed = await client.post("/teacher/kb", json=_note(), headers=teacher_headers)
    assert failed.status_code == 502
    assert failed.json()["detail"] == "Could not write to the knowledge base"
    pending = await client.get("/teacher/kb", params={"status": "pending"}, headers=teacher_headers)
    assert pending.json()["total"] == 1
    assert pending.json()["items"][0]["title"] == "B-tree pages"


async def test_bulk_review_reports_failed_ids(client, monkeypatch):
    written, _deleted = _spy(monkeypatch)
    _teacher_body, teacher_headers = await _teacher(client)
    first = (await client.post("/teacher/kb", json=_note(title="One", approve=False), headers=teacher_headers)).json()
    second = (await client.post("/teacher/kb", json=_note(title="Two", approve=False), headers=teacher_headers)).json()
    done = (
        await client.post("/teacher/kb", json=_note(title="Done", approve=True), headers=teacher_headers)
    ).json()

    rejected = await client.post(
        "/teacher/kb/bulk",
        json={"ids": [first["id"], "not-an-id", done["id"]], "action": "reject", "reason": "duplicate of the textbook"},
        headers=teacher_headers,
    )
    assert rejected.status_code == 200, rejected.text
    body = rejected.json()
    assert [item["id"] for item in body["updated"]] == [first["id"]]
    assert body["updated"][0]["status"] == "rejected"
    assert body["updated"][0]["reject_reason"] == "duplicate of the textbook"
    assert {row["id"] for row in body["failed"]} == {"not-an-id", done["id"]}
    assert written == [("Leaf nodes hold the keys.", "Done", "textbook")]

    approved = await client.post(
        "/teacher/kb/bulk",
        json={"ids": [second["id"], first["id"]], "action": "approve"},
        headers=teacher_headers,
    )
    assert [item["id"] for item in approved.json()["updated"]] == [second["id"]]
    assert approved.json()["failed"][0]["id"] == first["id"]
    assert len(written) == 2

    blank = await client.post(
        "/teacher/kb/bulk",
        json={"ids": [second["id"]], "action": "reject", "reason": "   "},
        headers=teacher_headers,
    )
    assert blank.status_code == 422
    assert (await client.post("/teacher/kb/bulk", json={"ids": [], "action": "approve"}, headers=teacher_headers)).status_code == 422


async def test_reject_reason_is_optional_unless_blank(client, monkeypatch):
    _spy(monkeypatch)
    _teacher_body, teacher_headers = await _teacher(client)
    item = (await client.post("/teacher/kb", json=_note(approve=False), headers=teacher_headers)).json()
    blank = await client.post(f"/teacher/kb/{item['id']}/reject", json={"reason": " "}, headers=teacher_headers)
    assert blank.status_code == 422
    omitted = await client.post(f"/teacher/kb/{item['id']}/reject", headers=teacher_headers)
    assert omitted.status_code == 200
    assert omitted.json()["status"] == "rejected"
    assert omitted.json()["reject_reason"] is None


async def test_validation_messages(client, monkeypatch):
    _spy(monkeypatch)
    _teacher_body, teacher_headers = await _teacher(client)
    missing = await client.post("/teacher/kb", json={"content": "x", "topic": "T"}, headers=teacher_headers)
    assert missing.status_code == 422
    assert missing.json()["detail"] == "Title is required"
    long_tags = await client.post(
        "/teacher/kb",
        json=_note(tags=["a", "b", "c", "d", "e", "f", "g", "h", "i"]),
        headers=teacher_headers,
    )
    assert long_tags.status_code == 422
    assert long_tags.json()["detail"] == "Use at most 8 tags"
    bad = await client.post("/teacher/kb", json=_note(difficulty="expert", source="rumor", type="poem"), headers=teacher_headers)
    assert bad.status_code == 422


async def test_uploads_chunk_approve_and_discard(client, monkeypatch):
    written, deleted = _spy(monkeypatch)
    _teacher_body, teacher_headers = await _teacher(client)
    markdown = b"# Joins\n\nAn inner join keeps matches.\n\n# Filters\n\nWHERE runs later.\n"
    uploaded = await client.post(
        "/teacher/kb/uploads",
        files={"file": ("lecture.md", markdown, "text/markdown")},
        headers=teacher_headers,
    )
    assert uploaded.status_code == 200, uploaded.text
    record = uploaded.json()
    assert record["status"] == "chunked"
    assert record["progress"] == 100
    assert [chunk["title"] for chunk in record["chunks"]] == ["Joins", "Filters"]
    assert record["kb_item_id"] is None

    listed = await client.get("/teacher/kb/uploads", headers=teacher_headers)
    assert listed.json()[0]["id"] == record["id"]

    approved = await client.post(
        f"/teacher/kb/uploads/{record['id']}/approve",
        json={"chunk_indexes": [0], "topic": "SQL", "tags": ["joins"]},
        headers=teacher_headers,
    )
    assert approved.status_code == 200, approved.text
    body = approved.json()
    assert body["item"]["status"] == "approved"
    assert body["item"]["type"] == "document"
    assert body["item"]["source"] == "upload"
    assert body["item"]["origin"] == "upload"
    assert body["item"]["topic"] == "SQL"
    assert "inner join" in body["item"]["content"]
    assert "WHERE" not in body["item"]["content"]
    assert body["upload"]["kb_item_id"] == body["item"]["id"]
    assert written[-1][2] == "upload"
    assert deleted == []

    again = await client.post(
        f"/teacher/kb/uploads/{record['id']}/approve",
        json={"chunk_indexes": [1], "topic": "SQL"},
        headers=teacher_headers,
    )
    assert again.status_code == 409
    discard = await client.delete(f"/teacher/kb/uploads/{record['id']}", headers=teacher_headers)
    assert discard.status_code == 409

    removed = await client.delete(f"/teacher/kb/{body['item']['id']}", headers=teacher_headers)
    assert removed.status_code == 200
    assert deleted == ["vec-1"]


async def test_upload_rejects_type_and_size_and_keeps_failed_rows(client, monkeypatch):
    _spy(monkeypatch)
    _teacher_body, teacher_headers = await _teacher(client)
    bad_type = await client.post(
        "/teacher/kb/uploads",
        files={"file": ("notes.exe", b"hello", "application/octet-stream")},
        headers=teacher_headers,
    )
    assert bad_type.status_code == 415
    too_big = await client.post(
        "/teacher/kb/uploads",
        files={"file": ("notes.txt", b"a" * (5_000_001), "text/plain")},
        headers=teacher_headers,
    )
    assert too_big.status_code == 413
    empty = await client.post(
        "/teacher/kb/uploads",
        files={"file": ("empty.txt", b"   ", "text/plain")},
        headers=teacher_headers,
    )
    assert empty.status_code == 200
    assert empty.json()["status"] == "failed"
    assert empty.json()["error"]
    early = await client.post(
        f"/teacher/kb/uploads/{empty.json()['id']}/approve",
        json={"topic": "Upload"},
        headers=teacher_headers,
    )
    assert early.status_code == 409
    discarded = await client.delete(f"/teacher/kb/uploads/{empty.json()['id']}", headers=teacher_headers)
    assert discarded.json() == {"id": empty.json()["id"], "deleted": True}
    assert (await client.get("/teacher/kb/uploads", headers=teacher_headers)).json() == []

    docx = io.BytesIO()
    with zipfile.ZipFile(docx, "w") as archive:
        archive.writestr(
            "word/document.xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
              <w:body><w:p><w:r><w:t>A hash index is a bucket of keys.</w:t></w:r></w:p></w:body>
            </w:document>""",
        )
    parsed = await client.post(
        "/teacher/kb/uploads",
        files={"file": ("hash.docx", docx.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        headers=teacher_headers,
    )
    assert parsed.status_code == 200, parsed.text
    assert parsed.json()["status"] == "chunked"
    assert "hash index" in parsed.json()["chunks"][0]["content"]


@pytest.mark.parametrize(
    "filename,payload",
    [
        ("notes.pdf", b"not a pdf"),
    ],
)
async def test_unreadable_pdf_is_a_failed_upload(client, monkeypatch, filename, payload):
    _spy(monkeypatch)
    _teacher_body, teacher_headers = await _teacher(client)
    response = await client.post(
        "/teacher/kb/uploads",
        files={"file": (filename, payload, "application/pdf")},
        headers=teacher_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert "PDF" in response.json()["error"]
