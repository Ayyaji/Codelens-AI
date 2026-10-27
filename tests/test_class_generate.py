"""AI drafts, shuffle, focus losses, duplicate, and teacher result stats.

Groq is mocked. The coding harness is the real sandbox.
"""

import csv
import io
import logging
import random

from rag_core.class_tests.shuffle import build_layout, present_questions
from rag_core.create_teacher import create_teacher_account
from rag_core.llm import AIBusy
from tests.conftest import register


def _mcq(index=0):
    return {
        "skill": "DBMS",
        "prompt": f"Which property is number {index}?",
        "options": ["Atomicity", "Latency", "Caching", "Paging"],
        "correct_index": 0,
        "explanation": "Atomicity means all or nothing.",
    }


def _coding():
    return {
        "title": "Add two numbers",
        "skill": "arrays",
        "statement": "Return the sum of the two integers.",
        "constraints": "The integers fit in a normal Python int.",
        "signature": "def add(a, b):",
        "explanation": "Add the two arguments.",
        "reference_solution": "def add(a, b):\n    return a + b",
        "visible_cases": [{"stdin": "[1, 2]", "expected": "3"}],
        "hidden_cases": [{"stdin": "[4, 5]", "expected": "9"}, {"stdin": "[0, 0]", "expected": "0"}],
    }


def _install(monkeypatch, handler):
    monkeypatch.setattr("rag_core.class_tests.generate.complete_json", handler)


async def _teacher(client, email="teacher-gen@school.edu"):
    await create_teacher_account("Ada Rao", email, "password123")
    response = await client.post("/auth/login", json={"email": email, "password": "password123"})
    assert response.status_code == 200, response.text
    body = response.json()
    return {"Authorization": f"Bearer {body['token']}"}


def _paper(**overrides):
    body = {
        "title": "Generated quiz",
        "topic": "DSA",
        "test_type": "mixed",
        "duration_minutes": 15,
        "published": True,
        "questions": [
            {
                "id": "one",
                "type": "mcq",
                "skill": "DBMS",
                "prompt": "First?",
                "options": ["Atomicity", "Latency", "Caching", "Paging"],
                "correct_index": 0,
                "explanation": "Atomicity.",
            },
            {
                "id": "two",
                "type": "mcq",
                "skill": "OS",
                "prompt": "Second?",
                "options": ["Kernel", "Pixel", "Font", "Cable"],
                "correct_index": 0,
                "explanation": "Kernel.",
            },
        ],
    }
    body.update(overrides)
    return body


async def test_student_cannot_generate_and_counts_are_checked(client):
    _student, headers = await register(client)
    denied = await client.post(
        "/teacher/class-tests/generate",
        json={"syllabus": "Binary search trees", "mcq_count": 1},
        headers=headers,
    )
    assert denied.status_code == 403

    teacher = await _teacher(client)
    missing = await client.post("/teacher/class-tests/generate", json={"syllabus": "a", "mcq_count": 1}, headers=teacher)
    assert missing.status_code == 422
    too_many = await client.post(
        "/teacher/class-tests/generate",
        json={"syllabus": "Binary search", "mcq_count": 9},
        headers=teacher,
    )
    assert too_many.status_code == 422
    language = await client.post(
        "/teacher/class-tests/generate",
        json={"syllabus": "Binary search", "coding_count": 1, "language": "java"},
        headers=teacher,
    )
    assert language.status_code == 422


async def test_generate_repairs_mcqs_and_keeps_a_coding_problem_that_passes(client, monkeypatch):
    teacher = await _teacher(client)
    calls = {"n": 0}

    def fake(_size, prompt):
        calls["n"] += 1
        if "KIND: coding" in prompt:
            return _coding()
        if calls["n"] == 1:
            return {"questions": [{"prompt": "Bad", "options": ["only", "two"], "correct_index": 0, "explanation": "no"}]}
        return {"questions": [_mcq(1)]}

    _install(monkeypatch, fake)
    response = await client.post(
        "/teacher/class-tests/generate",
        json={"syllabus": "ACID and sums", "difficulty": "easy", "mcq_count": 1, "coding_count": 1, "use_kb": False},
        headers=teacher,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert calls["n"] >= 2
    kinds = [question["type"] for question in body["questions"]]
    assert kinds == ["mcq", "coding"]
    mcq = body["questions"][0]
    assert len(mcq["options"]) == 4
    assert mcq["correct_index"] == 0
    assert mcq["explanation"]
    coding = body["questions"][1]
    assert "def add(a, b):" in coding["starter_code"]
    assert "if __name__" in coding["starter_code"]
    assert coding["visible_cases"][0]["expected"] == "3"
    assert coding["hidden_cases"][0]["stdin"] == "[4, 5]"
    assert "reference_solution" not in response.text
    assert "return a + b" not in response.text
    assert body["busy"] is False


async def test_failed_reference_solution_is_flagged_not_returned(client, monkeypatch):
    teacher = await _teacher(client)

    def fake(_size, prompt):
        payload = _coding()
        payload["reference_solution"] = "def add(a, b):\n    return 0"
        return payload

    _install(monkeypatch, fake)
    response = await client.post(
        "/teacher/class-tests/generate",
        json={"syllabus": "Adding integers", "coding_count": 1},
        headers=teacher,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["questions"] == []
    assert body["flagged"][0]["type"] == "coding"
    assert "failed" in body["flagged"][0]["reason"].lower() or "expected" in body["flagged"][0]["reason"]
    assert body["partial"] is True


async def test_busy_pool_is_503_or_a_partial_draft(client, monkeypatch):
    teacher = await _teacher(client)

    def always_busy(_size, _prompt):
        raise AIBusy()

    _install(monkeypatch, always_busy)
    busy = await client.post(
        "/teacher/class-tests/generate",
        json={"syllabus": "Hash maps", "mcq_count": 1},
        headers=teacher,
    )
    assert busy.status_code == 503
    assert busy.json()["detail"] == "AI service is busy, please try again in a few seconds"

    calls = {"n": 0}

    def partial(_size, prompt):
        calls["n"] += 1
        if calls["n"] == 1:
            count = 3
            return {"questions": [_mcq(i) for i in range(count)]}
        raise AIBusy()

    _install(monkeypatch, partial)
    response = await client.post(
        "/teacher/class-tests/generate",
        json={"syllabus": "Hash maps and sets", "mcq_count": 4},
        headers=teacher,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["questions"]) == 3
    assert body["busy"] is True
    assert body["partial"] is True


async def test_generate_can_use_the_knowledge_base_without_logging_the_syllabus(client, monkeypatch, caplog):
    teacher = await _teacher(client)
    seen = {}

    def fake_context(query, k=2):
        seen["query"] = query
        seen["k"] = k
        return "Atomicity means every write lands or none do."

    def fake(_size, prompt):
        seen["prompt"] = prompt
        return {"questions": [_mcq()]}

    monkeypatch.setattr("rag_core.agents.retrieval.get_context", fake_context)
    _install(monkeypatch, fake)
    secret = "syllabus-secret-token about transactions"
    with caplog.at_level(logging.INFO):
        response = await client.post(
            "/teacher/class-tests/generate",
            json={"syllabus": secret, "mcq_count": 1, "use_kb": True},
            headers=teacher,
        )
    assert response.status_code == 200, response.text
    assert "Atomicity means every write" in seen["prompt"]
    assert secret not in caplog.text
    assert "gsk_" not in caplog.text


async def test_empty_knowledge_base_warns_and_still_drafts(client, monkeypatch):
    teacher = await _teacher(client)
    monkeypatch.setattr("rag_core.agents.retrieval.get_context", lambda *_args, **_kwargs: "")
    _install(monkeypatch, lambda _size, _prompt: {"questions": [_mcq()]})
    response = await client.post(
        "/teacher/class-tests/generate",
        json={"syllabus": "Operating systems", "mcq_count": 1, "use_kb": True},
        headers=teacher,
    )
    assert response.status_code == 200, response.text
    assert response.json()["questions"]
    assert any("knowledge base" in warning.lower() for warning in response.json()["warnings"])


async def test_saved_questions_show_up_in_the_bank(client, monkeypatch):
    teacher = await _teacher(client)
    _install(monkeypatch, lambda _size, _prompt: {"questions": [_mcq()]})
    generated = await client.post(
        "/teacher/class-tests/generate",
        json={"syllabus": "Transactions", "mcq_count": 1},
        headers=teacher,
    )
    question = generated.json()["questions"][0]
    saved = await client.post("/teacher/question-bank", json={"questions": [question]}, headers=teacher)
    assert saved.status_code == 200, saved.text
    assert saved.json()["saved"] == 1
    listed = await client.get("/teacher/question-bank?kind=mcq&topic=DBMS", headers=teacher)
    prompts = [item["prompt"] for item in listed.json()["questions"]]
    assert question["prompt"] in prompts
    assert listed.json()["totals"]["mcq"] >= 26


async def test_duplicate_is_an_unpublished_copy(client):
    teacher = await _teacher(client)
    created = await client.post("/teacher/class-tests", json=_paper(published=True, title="Friday"), headers=teacher)
    assert created.status_code == 200, created.text
    copy = await client.post(f"/teacher/class-tests/{created.json()['id']}/duplicate", headers=teacher)
    assert copy.status_code == 200, copy.text
    body = copy.json()
    assert body["id"] != created.json()["id"]
    assert body["published"] is False
    assert body["title"].endswith("(copy)")
    assert body["attempt_count"] == 0
    assert body["questions"][0]["id"] != created.json()["questions"][0]["id"]
    assert body["questions"][0]["prompt"] == "First?"


async def test_shuffle_is_stable_and_grading_uses_the_option_text(client, monkeypatch):
    def reverse(self, seq):
        seq.reverse()

    monkeypatch.setattr(random.Random, "shuffle", reverse)
    teacher = await _teacher(client)
    _student, student_headers = await register(client, email="shuffle@example.com")
    created = await client.post(
        "/teacher/class-tests",
        json=_paper(shuffle_questions=True, shuffle_options=True, show_answers_after_submit=True),
        headers=teacher,
    )
    test_id = created.json()["id"]
    started = await client.post(f"/class-tests/{test_id}/start", headers=student_headers)
    assert started.status_code == 200, started.text
    view = started.json()
    assert [question["id"] for question in view["questions"]] == ["two", "one"]
    first = view["questions"][0]
    assert first["options"][0] == "Cable"
    assert "correct_index" not in first
    again = await client.post(f"/class-tests/{test_id}/start", headers=student_headers)
    assert [question["id"] for question in again.json()["questions"]] == ["two", "one"]
    submitted = await client.post(
        f"/class-tests/{test_id}/submit",
        json={"answers": [{"question_id": "one", "selected": "Atomicity"}, {"question_id": "two", "selected": "Kernel"}]},
        headers=student_headers,
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["score"] == 100.0
    revealed = {question["id"]: question for question in submitted.json()["questions"]}
    assert revealed["two"]["options"][0] == "Cable"
    assert revealed["two"]["correct_index"] == 3


async def test_layout_helper_is_a_permutation():
    test = {"_id": "abc", "shuffle_questions": True, "shuffle_options": True, "questions": _paper()["questions"]}
    first = build_layout(test, "attempt-1")
    assert build_layout(test, "attempt-1") == first
    assert sorted(first["question_order"]) == ["one", "two"]
    assert sorted(first["option_map"]["one"]) == [0, 1, 2, 3]
    shown = present_questions(test["questions"], first)
    assert {question["id"] for question in shown} == {"one", "two"}


async def test_focus_loss_question_stats_and_csv(client):
    teacher = await _teacher(client)
    _student, student_headers = await register(client, email="focus@example.com", name="=Ada")
    created = await client.post("/teacher/class-tests", json=_paper(test_type="mcq"), headers=teacher)
    test_id = created.json()["id"]
    assert created.json()["attempt_count"] == 0
    started = await client.post(f"/class-tests/{test_id}/start", headers=student_headers)
    assert started.status_code == 200
    first = await client.post(f"/class-tests/{test_id}/focus", headers=student_headers)
    second = await client.post(f"/class-tests/{test_id}/focus", headers=student_headers)
    assert first.status_code == 200 and second.json()["focus_loss_count"] == 2
    await client.post(
        f"/class-tests/{test_id}/submit",
        json={"answers": [{"question_id": "one", "selected": "Atomicity"}, {"question_id": "two", "selected": "Pixel"}]},
        headers=student_headers,
    )
    report = await client.get(f"/teacher/class-tests/{test_id}/attempts", headers=teacher)
    assert report.status_code == 200, report.text
    body = report.json()
    assert body["attempts"][0]["focus_loss_count"] == 2
    stats = {item["question_id"]: item for item in body["question_stats"]}
    assert stats["one"]["percent_correct"] == 100.0
    assert stats["two"]["percent_correct"] == 0.0
    loaded = await client.get(f"/teacher/class-tests/{test_id}", headers=teacher)
    assert loaded.json()["attempt_count"] == 1
    blocked = await client.put(
        f"/teacher/class-tests/{test_id}",
        json={"questions": created.json()["questions"][:1], "test_type": "mcq", "title": "Generated quiz", "duration_minutes": 15, "topic": "DSA"},
        headers=teacher,
    )
    assert blocked.status_code == 409

    exported = await client.get(f"/teacher/class-tests/{test_id}/attempts.csv", headers=teacher)
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/csv")
    rows = list(csv.reader(io.StringIO(exported.text)))
    assert rows[0][0] == "student_name"
    assert rows[1][1] == "focus@example.com"
    assert rows[1][5] == "2"
    assert rows[1][0].startswith("'")


async def test_upcoming_tests_stay_hidden_unless_requested(client):
    _student, student_headers = await register(client, email="soon@example.com")
    teacher = await _teacher(client)
    future = await client.post(
        "/teacher/class-tests",
        json=_paper(title="Later", available_from="2099-01-01T00:00:00Z"),
        headers=teacher,
    )
    test_id = future.json()["id"]
    hidden = await client.get("/class-tests", headers=student_headers)
    assert hidden.json()["tests"] == []
    assert "server_now" in hidden.json()
    listed = await client.get("/class-tests?include_upcoming=1", headers=student_headers)
    assert listed.status_code == 200
    tests = listed.json()["tests"]
    assert len(tests) == 1
    assert tests[0]["phase"] == "upcoming"
    assert tests[0]["can_start"] is False
    assert tests[0]["available_from"]
    opened = await client.get(f"/class-tests/{test_id}", headers=student_headers)
    assert opened.status_code == 200
    assert opened.json()["phase"] == "upcoming"
    assert (await client.post(f"/class-tests/{test_id}/start", headers=student_headers)).status_code == 404


async def test_jd_generate_route_is_unchanged(client):
    _student, headers = await register(client, email="jd-flow@example.com")
    response = await client.post("/test/generate", json={"jd_id": "missing"}, headers=headers)
    assert response.status_code == 404
