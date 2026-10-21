"""HTTP contract for the two modules. The model is replaced with a stub."""

import pytest
from fastapi.testclient import TestClient

from rag_core.api import app

SKILLS = {
    "skills": [
        {
            "name": "SQL",
            "level": "intermediate",
            "explanation": "The role writes queries against a relational database.",
        },
        {
            "name": "Python",
            "level": "intermediate",
            "explanation": "The role uses Python for small data tasks.",
        },
    ],
    "roadmap": [
        {
            "order": 1,
            "skill": "SQL",
            "goal": "Filter and join tables",
            "practice": "Write three joins",
        },
        {
            "order": 2,
            "skill": "Python",
            "goal": "Handle stdin problems",
            "practice": "Solve two stdin scripts",
        },
    ],
}

QUESTIONS = {
    "questions": [
        {
            "id": "q1",
            "type": "mcq",
            "skill": "SQL",
            "prompt": "Which clause filters rows?",
            "options": ["SELECT", "WHERE", "ORDER BY", "GROUP BY"],
            "answer": "WHERE",
        },
        {
            "id": "c1",
            "type": "coding",
            "skill": "Python",
            "prompt": "Read a line and print it back.",
            "language": "python",
            "starter_code": "",
            "test_cases": [
                {"input": "ok\n", "expected": "ok"},
                {"input": "hidden-secret\n", "expected": "hidden-secret"},
            ],
        },
    ]
}


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def _stub_model(monkeypatch):
    calls = {"parse": 0, "questions": 0, "explain": 0}

    def fake(size, prompt):
        if prompt.startswith("Parse this job description"):
            calls["parse"] += 1
            assert size == "small"
            return SKILLS
        if prompt.startswith("Write an interview practice test"):
            calls["questions"] += 1
            assert size == "small"
            return QUESTIONS
        if prompt.startswith("You explain why"):
            calls["explain"] += 1
            assert size == "large"
            return {"explanation": "WHERE filters rows."}
        raise AssertionError(prompt[:60])

    monkeypatch.setattr("rag_core.llm.complete_json", fake)
    return calls


def test_ask_returns_answer_agent_and_directive(client, monkeypatch):
    monkeypatch.setattr(
        "rag_core.api.run_pipeline",
        lambda query, student_id="anonymous", profile=False: {
            "query": query,
            "agent_used": "debug",
            "answer": "Define x before you use it.",
            "directive": "hint",
            "response_time": 0.2,
        },
    )
    response = client.post("/ask", json={"student_id": "s1", "query": "NameError on x"})
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Define x before you use it."
    assert body["agent_used"] == "debug"
    assert body["directive"] == "hint"


def test_ask_rejects_a_blank_query(client):
    response = client.post("/ask", json={"student_id": "s1", "query": " "})
    assert response.status_code == 422


def test_jd_test_flow_caches_the_model_and_hides_the_answer_key(client, monkeypatch):
    calls = _stub_model(monkeypatch)
    uploaded = client.post(
        "/jd/upload",
        json={"text": "We need a Python developer who writes SQL every day."},
    )
    assert uploaded.status_code == 200
    jd_id = uploaded.json()["jd_id"]
    assert set(uploaded.json()) == {"jd_id"}

    first = client.get(f"/jd/analyse/{jd_id}")
    second = client.get(f"/jd/analyse/{jd_id}")
    assert first.status_code == 200
    assert first.json()["skills"][0]["name"] == "SQL"
    assert "roadmap" in first.json()
    assert second.json() == first.json()
    assert calls["parse"] == 1

    generated = client.post("/test/generate", json={"jd_id": jd_id})
    again = client.post("/test/generate", json={"jd_id": jd_id})
    assert generated.status_code == 200
    body = generated.json()
    assert body["jd_id"] == jd_id
    assert again.json()["questions"] == body["questions"]
    assert calls["questions"] == 1
    mcq = body["questions"][0]
    coding = body["questions"][1]
    assert "answer" not in mcq
    assert mcq["options"][1] == "WHERE"
    assert "hidden-secret" not in str(body)
    assert coding["sample_output"] == "ok"

    missing = client.get("/jd/analyse/does-not-exist")
    assert missing.status_code == 404

    submitted = client.post(
        "/test/submit",
        json={
            "student_id": "s1",
            "jd_id": jd_id,
            "answers": [
                {"question_id": "q1", "selected": "SELECT"},
                {"question_id": "c1", "code": "import sys\nprint(sys.stdin.read().strip())\n"},
            ],
        },
    )
    assert submitted.status_code == 200
    result = submitted.json()
    assert set(result) == {"score", "weak_topics", "guidance"}
    assert result["score"] == 50.0
    assert result["weak_topics"] == ["SQL"]
    assert result["guidance"]["directive"] == "full"
    assert "WHERE filters rows." in result["guidance"]["message"]
    assert calls["explain"] == 1


def test_run_returns_stdout_and_stderr(client):
    response = client.post("/run", json={"code": "print(1 + 1)", "language": "python"})
    assert response.status_code == 200
    assert response.json() == {"stdout": "2\n", "stderr": ""}


def test_run_feeds_sample_stdin(client):
    response = client.post(
        "/run",
        json={
            "code": "print(int(input()) * 2)",
            "language": "python",
            "stdin": "2\n",
        },
    )
    assert response.status_code == 200
    assert response.json() == {"stdout": "4\n", "stderr": ""}


def test_cors_allows_the_vite_dev_origin(client):
    live = client.get("/", headers={"Origin": "http://localhost:5173"})
    assert live.headers["access-control-allow-origin"] in {"*", "http://localhost:5173"}

    preflight = client.options(
        "/jd/upload",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] in {"*", "http://127.0.0.1:5173"}
    assert "POST" in preflight.headers["access-control-allow-methods"]


def test_text_file_upload(client, monkeypatch):
    _stub_model(monkeypatch)
    response = client.post(
        "/jd/upload",
        files={"file": ("role.txt", b"Python and SQL for the backend role.", "text/plain")},
    )
    assert response.status_code == 200
    assert response.json()["jd_id"]


def test_submit_before_generate_is_404(client, monkeypatch):
    _stub_model(monkeypatch)
    uploaded = client.post("/jd/upload", json={"text": "Python developer"})
    jd_id = uploaded.json()["jd_id"]
    response = client.post(
        "/test/submit",
        json={"student_id": "s1", "jd_id": jd_id, "answers": [{"question_id": "q1", "selected": "A"}]},
    )
    assert response.status_code == 404


def test_router_skips_the_model_for_bugs_and_hints(monkeypatch):
    def explode(_query):
        raise AssertionError("router should not call the model")

    monkeypatch.setattr("rag_core.router._llm_route", explode)
    from rag_core.router import route_query

    assert route_query("I'm getting NameError: name 'x' is not defined") == "debug"
    assert route_query("Give me a hint for fixing IndexError") == "hint"


def test_router_uses_the_model_for_an_ambiguous_question(monkeypatch):
    monkeypatch.setattr("rag_core.router._llm_route", lambda _query: "concept")
    from rag_core.router import route_query

    assert route_query("What is a hash map?") == "concept"
