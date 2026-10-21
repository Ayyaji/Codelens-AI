"""Auth, roles, the knowledge-base gate, chats, and persona updates."""

import pytest

from rag_core.auth import create_token
from rag_core.create_teacher import create_teacher_account
from tests.conftest import register
from tests.test_api import _stub_model


async def _teacher(client):
    await create_teacher_account("Ada Rao", "ada@school.edu", "password123")
    response = await client.post(
        "/auth/login",
        json={"email": "ada@school.edu", "password": "password123"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["user"]["role"] == "teacher"
    return body, {"Authorization": f"Bearer {body['token']}"}


async def test_register_and_login_return_the_token_shape(client):
    body, headers = await register(client, email="Ada@Example.com", name=" Ada ")
    assert set(body) == {"token", "user"}
    assert set(body["user"]) == {"id", "name", "email", "role"}
    assert body["user"]["email"] == "ada@example.com"
    assert body["user"]["name"] == "Ada"
    assert body["user"]["role"] == "student"
    assert "password" not in body["user"]

    me = await client.get("/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json() == body["user"]

    again = await client.post(
        "/auth/login",
        json={"email": "ADA@example.com", "password": "password123"},
    )
    assert again.status_code == 200
    assert again.json()["user"] == body["user"]


async def test_duplicate_email_and_teacher_self_register_are_refused(client):
    await register(client)
    duplicate = await client.post(
        "/auth/register",
        json={"name": "Other", "email": "student@example.com", "password": "password123"},
    )
    assert duplicate.status_code == 409

    teacher = await client.post(
        "/auth/register",
        json={"name": "Ada", "email": "ada@school.edu", "password": "password123", "role": "teacher"},
    )
    assert teacher.status_code == 403

    bad = await client.post("/auth/login", json={"email": "missing@example.com", "password": "password123"})
    wrong = await client.post("/auth/login", json={"email": "student@example.com", "password": "not-the-password"})
    assert bad.status_code == 401
    assert wrong.status_code == 401
    assert bad.json()["detail"] == wrong.json()["detail"]


async def test_student_routes_require_a_token(client):
    assert (await client.post("/ask", json={"query": "hello"})).status_code == 401
    assert (await client.get("/me/persona")).status_code == 401
    assert (await client.post("/run", json={"code": "print(1)", "language": "python"})).status_code == 401
    assert (await client.get("/teacher/overview")).status_code == 401


async def test_a_forged_teacher_claim_does_not_grant_the_role(client):
    body, _headers = await register(client)
    forged = create_token(body["user"]["id"], "teacher")
    response = await client.get("/teacher/overview", headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 403


async def test_disabled_users_are_blocked(client):
    body, headers = await register(client)
    _teacher_body, teacher_headers = await _teacher(client)
    disabled = await client.patch(
        f"/teacher/students/{body['user']['id']}",
        json={"disabled": True},
        headers=teacher_headers,
    )
    assert disabled.status_code == 200
    assert disabled.json()["disabled"] is True

    assert (await client.get("/auth/me", headers=headers)).status_code == 403
    assert (await client.post("/ask", json={"query": "hello"}, headers=headers)).status_code == 403
    login = await client.post(
        "/auth/login",
        json={"email": "student@example.com", "password": "password123"},
    )
    assert login.status_code == 403

    enabled = await client.patch(
        f"/teacher/students/{body['user']['id']}",
        json={"disabled": False},
        headers=teacher_headers,
    )
    assert enabled.json()["disabled"] is False
    assert (await client.get("/auth/me", headers=headers)).status_code == 200


async def test_students_cannot_open_teacher_routes_and_old_routes_are_gone(client):
    _body, headers = await register(client)
    _teacher_body, teacher_headers = await _teacher(client)
    assert (await client.get("/teacher/overview", headers=headers)).status_code == 403
    assert (await client.get("/teacher/students", headers=headers)).status_code == 403
    overview = await client.get("/teacher/overview", headers=teacher_headers)
    assert overview.status_code == 200
    assert overview.json()["total_students"] == 1
    assert overview.json()["directive_counts"] == {"full": 0, "hint": 0, "gentle": 0, "break": 0}

    for path in ("/pending-kb", "/sessions", "/approve-kb/1", "/reject-kb/1"):
        assert (await client.get(path, headers=teacher_headers)).status_code == 404
        assert (await client.post(path, headers=teacher_headers)).status_code == 404


async def test_chats_belong_to_the_token_user(client, monkeypatch):
    seen = {}

    async def fake(query, student_id="anonymous", profile=False):
        seen["student_id"] = student_id
        return {"answer": "ok", "agent_used": "debug", "directive": "hint", "response_time": 0.1}

    monkeypatch.setattr("rag_core.api.run_pipeline", fake)
    ada, ada_headers = await register(client, email="ada@example.com", name="Ada")
    _bea, bea_headers = await register(client, email="bea@example.com", name="Bea")

    first = await client.post(
        "/ask",
        json={"query": "Why NameError?", "student_id": "someone-else"},
        headers=ada_headers,
    )
    assert first.status_code == 200
    assert seen["student_id"] == ada["user"]["id"]
    chat_id = first.json()["chat_id"]

    second = await client.post("/ask", json={"query": "And again?", "chat_id": chat_id}, headers=ada_headers)
    assert second.status_code == 200
    assert second.json()["chat_id"] == chat_id

    listing = await client.get("/me/chats", headers=ada_headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert listing.json()[0]["chat_id"] == chat_id

    detail = await client.get(f"/me/chats/{chat_id}", headers=ada_headers)
    assert len(detail.json()["messages"]) == 4
    assert (await client.get("/me/chats", headers=bea_headers)).json() == []
    assert (await client.get(f"/me/chats/{chat_id}", headers=bea_headers)).status_code == 404
    stolen = await client.post("/ask", json={"query": "nope", "chat_id": chat_id}, headers=bea_headers)
    assert stolen.status_code == 404


async def test_ask_reads_history_and_updates_the_persona(client, monkeypatch):
    monkeypatch.setattr("rag_core.pipeline.route_query", lambda _query: "debug")
    monkeypatch.setattr(
        "rag_core.agents.debug.debug_agent",
        lambda query, directive="full": "Define x before you use it.",
    )
    body, headers = await register(client)
    _teacher_body, teacher_headers = await _teacher(client)

    first = await client.post("/ask", json={"query": "NameError on x"}, headers=headers)
    second = await client.post(
        "/ask",
        json={"query": "NameError on x again", "chat_id": first.json()["chat_id"]},
        headers=headers,
    )
    assert first.json()["directive"] == "full"
    assert second.json()["directive"] == "hint"

    detail = await client.get(f"/teacher/students/{body['user']['id']}", headers=teacher_headers)
    assert detail.status_code == 200
    notes = detail.json()["persona"]["learning_notes"]
    assert len(notes) == 2
    assert notes[0].startswith("full via debug")
    assert notes[1].startswith("hint via debug")


async def test_web_results_reach_chroma_only_when_a_teacher_approves(client, monkeypatch):
    written = []

    def spy(content, query, source):
        written.append((content, query, source))

    monkeypatch.setattr("rag_core.kb_update.write_kb_document", spy)
    monkeypatch.setattr("rag_core.pipeline.route_query", lambda _query: "web")
    monkeypatch.setattr(
        "rag_core.agents.web.web_agent",
        lambda query: {
            "answer": "From the web.",
            "source": "https://example.com/note",
            "raw_content": "raw notes about the question",
        },
    )
    body, headers = await register(client)
    _teacher_body, teacher_headers = await _teacher(client)

    asked = await client.post("/ask", json={"query": "What is a WAL?"}, headers=headers)
    assert asked.status_code == 200
    assert written == []

    pending = await client.get("/teacher/kb/pending", headers=teacher_headers)
    assert pending.status_code == 200
    item = pending.json()[0]
    assert item["content"] == "raw notes about the question"
    assert item["proposed_by"] == body["user"]["id"]
    assert item["status"] == "pending"
    assert (await client.post(f"/teacher/kb/{item['id']}/approve", headers=headers)).status_code == 403
    assert written == []

    edited = await client.put(
        f"/teacher/kb/{item['id']}",
        json={"content": "teacher edited notes"},
        headers=teacher_headers,
    )
    assert edited.status_code == 200
    assert written == []

    approved = await client.post(f"/teacher/kb/{item['id']}/approve", headers=teacher_headers)
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert written == [("teacher edited notes", "What is a WAL?", "https://example.com/note")]

    again = await client.post(f"/teacher/kb/{item['id']}/approve", headers=teacher_headers)
    assert again.status_code == 409
    assert written == [("teacher edited notes", "What is a WAL?", "https://example.com/note")]

    asked_again = await client.post("/ask", json={"query": "What is a checkpoint?"}, headers=headers)
    assert asked_again.status_code == 200
    pending = await client.get("/teacher/kb/pending", headers=teacher_headers)
    other = pending.json()[0]
    rejected = await client.post(f"/teacher/kb/{other['id']}/reject", headers=teacher_headers)
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert len(written) == 1
    assert (await client.get("/teacher/kb/pending", headers=teacher_headers)).json() == []


async def test_teacher_dashboard_sees_scores_and_can_reset(client, monkeypatch):
    _stub_model(monkeypatch)
    body, headers = await register(client)
    _teacher_body, teacher_headers = await _teacher(client)

    uploaded = await client.post("/jd/upload", json={"text": "Python and SQL role."}, headers=headers)
    jd_id = uploaded.json()["jd_id"]
    await client.get(f"/jd/analyse/{jd_id}", headers=headers)
    await client.post("/test/generate", json={"jd_id": jd_id}, headers=headers)
    submitted = await client.post(
        "/test/submit",
        json={
            "jd_id": jd_id,
            "answers": [
                {"question_id": "q1", "selected": "SELECT"},
                {"question_id": "c1", "code": "import sys\nprint(sys.stdin.read().strip())\n"},
            ],
        },
        headers=headers,
    )
    assert submitted.json()["score"] == 50.0

    overview = await client.get("/teacher/overview", headers=teacher_headers)
    assert overview.json()["total_students"] == 1
    assert overview.json()["active_today"] == 1
    assert overview.json()["avg_score"] == 50.0
    assert overview.json()["directive_counts"]["full"] == 1
    assert overview.json()["pending_kb"] == 0

    rows = await client.get("/teacher/students", headers=teacher_headers)
    row = rows.json()[0]
    assert row["id"] == body["user"]["id"]
    assert row["avg_score"] == 50.0
    assert row["weak_topics"] == ["SQL"]
    assert row["last_active"]

    feed = await client.get("/teacher/activity", params={"limit": 2}, headers=teacher_headers)
    assert feed.status_code == 200
    assert len(feed.json()) == 2
    assert feed.json()[0]["user_id"] == body["user"]["id"]
    assert (await client.get("/teacher/activity", params={"limit": 0}, headers=teacher_headers)).status_code == 422

    reset = await client.post(f"/teacher/students/{body['user']['id']}/reset", headers=teacher_headers)
    assert reset.status_code == 200
    assert reset.json() == {"id": body["user"]["id"], "reset": True}
    persona = await client.get("/me/persona", headers=headers)
    assert persona.json() == {"weak_topics": [], "mistake_patterns": [], "scores": [], "jds": []}
    history = await client.get("/me/history", headers=headers)
    assert history.json() == {"jds": [], "tests": []}
    assert (await client.get("/me/chats", headers=headers)).json() == []
    # The account is still usable. Reset does not disable it.
    assert (await client.get("/auth/me", headers=headers)).status_code == 200


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/pending-kb"),
        ("get", "/sessions"),
        ("post", "/approve-kb/1"),
        ("post", "/reject-kb/1"),
    ],
)
async def test_removed_routes_stay_missing_without_a_token(client, method, path):
    response = await getattr(client, method)(path)
    assert response.status_code == 404
