"""HTTP contract for JD upload, tests, and guidance. The model is replaced with a stub."""

from tests.conftest import register

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


async def test_ask_returns_answer_agent_directive_and_chat(client, monkeypatch):
    async def fake(query, student_id="anonymous", profile=False):
        return {
            "query": query,
            "agent_used": "debug",
            "answer": "Define x before you use it.",
            "directive": "hint",
            "response_time": 0.2,
        }

    monkeypatch.setattr("rag_core.api.run_pipeline", fake)
    _, headers = await register(client)
    response = await client.post("/ask", json={"student_id": "someone-else", "query": "NameError on x"}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"answer", "agent_used", "directive", "chat_id"}
    assert body["answer"] == "Define x before you use it."
    assert body["agent_used"] == "debug"
    assert body["directive"] == "hint"

    saved = await client.get(f"/me/chats/{body['chat_id']}", headers=headers)
    assert saved.status_code == 200
    messages = saved.json()["messages"]
    assert [item["role"] for item in messages] == ["user", "assistant"]
    assert messages[1]["directive"] == "hint"
    assert messages[1]["agent_used"] == "debug"


async def test_ask_rejects_a_blank_query(client):
    _, headers = await register(client)
    response = await client.post("/ask", json={"query": " "}, headers=headers)
    assert response.status_code == 422


async def test_jd_test_flow_caches_the_model_and_hides_the_answer_key(client, monkeypatch):
    calls = _stub_model(monkeypatch)
    _, headers = await register(client)
    uploaded = await client.post(
        "/jd/upload",
        json={"text": "We need a Python developer who writes SQL every day."},
        headers=headers,
    )
    assert uploaded.status_code == 200
    jd_id = uploaded.json()["jd_id"]
    assert set(uploaded.json()) == {"jd_id"}

    first = await client.get(f"/jd/analyse/{jd_id}", headers=headers)
    second = await client.get(f"/jd/analyse/{jd_id}", headers=headers)
    assert first.status_code == 200
    assert first.json()["skills"][0]["name"] == "SQL"
    assert "roadmap" in first.json()
    assert second.json() == first.json()
    assert calls["parse"] == 1

    generated = await client.post("/test/generate", json={"jd_id": jd_id}, headers=headers)
    again = await client.post("/test/generate", json={"jd_id": jd_id}, headers=headers)
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

    missing = await client.get("/jd/analyse/does-not-exist", headers=headers)
    assert missing.status_code == 404

    submitted = await client.post(
        "/test/submit",
        json={
            "student_id": "someone-else",
            "jd_id": jd_id,
            "answers": [
                {"question_id": "q1", "selected": "SELECT"},
                {"question_id": "c1", "code": "import sys\nprint(sys.stdin.read().strip())\n"},
            ],
        },
        headers=headers,
    )
    assert submitted.status_code == 200
    result = submitted.json()
    assert set(result) == {"score", "weak_topics", "guidance"}
    assert result["score"] == 50.0
    assert result["weak_topics"] == ["SQL"]
    assert result["guidance"]["directive"] == "full"
    assert "WHERE filters rows." in result["guidance"]["message"]
    assert calls["explain"] == 1

    persona = await client.get("/me/persona", headers=headers)
    assert persona.status_code == 200
    assert persona.json()["weak_topics"] == ["SQL"]
    assert persona.json()["scores"][0]["score"] == 50.0
    history = await client.get("/me/history", headers=headers)
    assert history.json()["tests"][0]["score"] == 50.0
    assert {item["jd_id"] for item in history.json()["jds"]} == {jd_id}


async def test_run_returns_stdout_and_stderr(client):
    _, headers = await register(client)
    response = await client.post("/run", json={"code": "print(1 + 1)", "language": "python"}, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"stdout": "2\n", "stderr": ""}


async def test_run_feeds_sample_stdin(client):
    _, headers = await register(client)
    response = await client.post(
        "/run",
        json={
            "code": "print(int(input()) * 2)",
            "language": "python",
            "stdin": "2\n",
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json() == {"stdout": "4\n", "stderr": ""}


async def test_cors_allows_the_vite_dev_origin(client):
    live = await client.get("/", headers={"Origin": "http://localhost:5173"})
    assert live.headers["access-control-allow-origin"] in {"*", "http://localhost:5173"}

    preflight = await client.options(
        "/jd/upload",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,authorization",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] in {"*", "http://127.0.0.1:5173"}
    assert "POST" in preflight.headers["access-control-allow-methods"]
    allowed = preflight.headers["access-control-allow-headers"]
    assert "authorization" in allowed.lower()


async def test_text_file_upload(client, monkeypatch):
    _stub_model(monkeypatch)
    _, headers = await register(client)
    response = await client.post(
        "/jd/upload",
        files={"file": ("role.txt", b"Python and SQL for the backend role.", "text/plain")},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["jd_id"]


async def test_submit_before_generate_is_404(client, monkeypatch):
    _stub_model(monkeypatch)
    _, headers = await register(client)
    uploaded = await client.post("/jd/upload", json={"text": "Python developer"}, headers=headers)
    jd_id = uploaded.json()["jd_id"]
    response = await client.post(
        "/test/submit",
        json={"jd_id": jd_id, "answers": [{"question_id": "q1", "selected": "A"}]},
        headers=headers,
    )
    assert response.status_code == 404


async def test_another_student_cannot_read_the_job_description(client, monkeypatch):
    _stub_model(monkeypatch)
    _, owner = await register(client, email="owner@example.com")
    _, other = await register(client, email="other@example.com", name="Other")
    uploaded = await client.post("/jd/upload", json={"text": "Python developer who writes SQL."}, headers=owner)
    jd_id = uploaded.json()["jd_id"]
    assert (await client.get(f"/jd/analyse/{jd_id}", headers=other)).status_code == 404
    assert (await client.post("/test/generate", json={"jd_id": jd_id}, headers=other)).status_code == 404


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
